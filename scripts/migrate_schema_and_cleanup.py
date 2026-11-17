"""One-time cleanup explicitly authorized on 2026-11-05; preserves the active dataset."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime
import mysql.connector
from Model.application.config.settings import ROOT,database_options
from DAO.application.dao.connection import Database
from scripts.schema_snapshot import snapshot
from scripts.create_relationship_review_schema import comparable

SOURCE='ecommerce_vn_retailer_demo'
TARGET='ecommerce_relationship_review'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute-authorized-cleanup',action='store_true',required=True)
    parser.parse_args()
    options=database_options()
    assert options.pop('database')==SOURCE,'One-time migration requires the original active schema'
    conn=mysql.connector.connect(**options);cursor=conn.cursor()
    folder=ROOT/'database/backups'/('before_schema_cleanup_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    folder.mkdir(parents=True,exist_ok=False)
    report={'source':SOURCE,'target':TARGET,'backups':[],'deleted':[],'preservedData':{}}
    receipt=folder/'cleanup_receipt.json'
    def save(): receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        cursor.execute('SHOW DATABASES');schemas=[r[0] for r in cursor.fetchall()]
        victims=sorted(s for s in schemas if s.startswith('ecommerce_') and s!=TARGET)
        assert SOURCE in victims and TARGET in schemas
        assert all(re.fullmatch(r'ecommerce_[A-Za-z0-9_]+',s) for s in victims)
        report['approvedDeletionList']=victims;save()
        assert comparable(snapshot(Database(SOURCE)))==comparable(snapshot(Database(TARGET)))
        dumper=Path('C:/Program Files/MySQL/MySQL Server 9.7/bin/mysqldump.exe')
        assert dumper.is_file()
        environment=dict(os.environ,MYSQL_PWD=options['password'])
        # Test schemas are disposable; retain full dumps of both non-test datasets.
        for schema in [SOURCE,'ecommerce_electronics_demo']:
            if schema not in victims: continue
            dump=folder/(schema+'.sql')
            command=[str(dumper),'--host='+options['host'],'--port='+str(options['port']),
                     '--user='+options['user'],'--single-transaction','--no-tablespaces',
                     '--column-statistics=0','--hex-blob','--set-gtid-purged=OFF','--routines','--events','--triggers','--databases',schema]
            with dump.open('wb') as out:
                completed=subprocess.run(command,stdout=out,stderr=subprocess.PIPE,env=environment,timeout=120)
            assert completed.returncode==0,'Backup failed; cleanup was not started'
            assert dump.stat().st_size>100 and b'Dump completed' in dump.read_bytes()[-1000:],'Incomplete backup'
            report['backups'].append({'schema':schema,'file':str(dump.relative_to(ROOT)),
                                      'bytes':dump.stat().st_size,'sha256':hashlib.sha256(dump.read_bytes()).hexdigest()});save()
        tables=sorted(snapshot(Database(SOURCE)))
        conn.commit();conn.start_transaction()
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        try:
            for table in tables:
                cursor.execute('SELECT COUNT(*) FROM `'+TARGET+'`.`'+table+'`')
                assert cursor.fetchone()[0]==0,'Destination must be empty; no overwrite permitted'
                cursor.execute('SELECT * FROM `'+SOURCE+'`.`'+table+'`')
                rows=cursor.fetchall();columns=len(cursor.description)
                if rows:
                    cursor.executemany('INSERT INTO `'+TARGET+'`.`'+table+'` VALUES('+','.join(['%s']*columns)+')',rows)
            conn.commit()
        except Exception:
            conn.rollback();raise
        finally:
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        for table in tables:
            cursor.execute('SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s ORDER BY SEQ_IN_INDEX',(SOURCE,table,'PRIMARY'))
            primary=[r[0] for r in cursor.fetchall()];assert primary
            ordering=','.join('`'+c+'`' for c in primary)
            values=[]
            for schema in [SOURCE,TARGET]:
                cursor.execute('SELECT * FROM `'+schema+'`.`'+table+'` ORDER BY '+ordering)
                rows=cursor.fetchall()
                values.append((len(rows),hashlib.sha256(json.dumps(rows,default=str,ensure_ascii=False).encode('utf-8')).hexdigest()))
            assert values[0]==values[1],'Copied data differs for '+table
            report['preservedData'][table]={'rows':values[0][0],'sha256':values[0][1]}
        cursor.execute('SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_SCHEMA,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL',(TARGET,))
        for table,column,ref_schema,ref_table,ref_column in cursor.fetchall():
            assert ref_schema==TARGET,'Cross-schema foreign key detected'
            cursor.execute('SELECT COUNT(*) FROM `'+TARGET+'`.`'+table+'` t LEFT JOIN `'+TARGET+'`.`'+ref_table+'` r ON t.`'+column+'`=r.`'+ref_column+'` WHERE t.`'+column+'` IS NOT NULL AND r.`'+ref_column+'` IS NULL')
            assert cursor.fetchone()[0]==0,'Orphan foreign key after copy'
        conn.commit()
        report['dataVerified']=True;report['foreignKeysVerified']=True;save()
        for name in ['.env','.env.app']:
            path=ROOT/name
            text=path.read_text(encoding='utf-8')
            if re.search(r'^APP_DATABASE=',text,re.M):
                text=re.sub(r'^APP_DATABASE=.*$', 'APP_DATABASE='+TARGET,text,flags=re.M)
            elif name=='.env.app':text=text.rstrip()+'\nAPP_DATABASE='+TARGET+'\n'
            path.write_text(text,encoding='utf-8')
        report['configurationUpdated']=True;save()
        for schema in victims:
            cursor.execute('DROP DATABASE `'+schema+'`')
            report['deleted'].append(schema);save()
        cursor.execute('SHOW DATABASES');report['remainingSchemas']=[r[0] for r in cursor.fetchall()]
        assert [s for s in report['remainingSchemas'] if s.startswith('ecommerce_')]==[TARGET]
        save()
        (ROOT/'data/test_runs/schema_cleanup_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'activeSchema':TARGET,'copiedTables':len(tables),'copiedProducts':report['preservedData']['products']['rows'],
                          'deletedSchemas':len(report['deleted']),'remainingSchemas':report['remainingSchemas'],
                          'backupFolder':str(folder.relative_to(ROOT))},ensure_ascii=False,indent=2))
    finally:
        cursor.close();conn.close()


if __name__=='__main__':main()
