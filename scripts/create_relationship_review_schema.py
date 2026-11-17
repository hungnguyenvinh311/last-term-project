"""Create an empty schema copy and verify Customer--Accounts constraints by rollback."""
import json
from pathlib import Path
import mysql.connector
from Model.application.config.settings import ROOT,database_options
from DAO.application.dao.connection import Database
from scripts.schema_snapshot import snapshot

def comparable(definitions):
    # MySQL may spell an inherited UTF-8 character set explicitly after DDL replay.
    return {k:v.replace(' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci',' COLLATE utf8mb4_unicode_ci') for k,v in definitions.items()}


def main():
    source=Database()
    target='ecommerce_relationship_review'
    options=database_options();options.pop('database')
    conn=mysql.connector.connect(**options)
    cursor=conn.cursor()
    try:
        definitions=snapshot(source)
        cursor.execute('SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s',(target,))
        exists=bool(cursor.fetchone()[0])
        if exists:
            assert comparable(snapshot(Database(target)))==comparable(definitions),'Existing review schema differs; no changes permitted'
            for table in definitions:
                cursor.execute('SELECT COUNT(*) FROM `'+target+'`.`'+table+'`')
                assert cursor.fetchone()[0]==0,'Existing review schema is not empty; no changes permitted'
        else:
            cursor.execute('CREATE DATABASE `'+target+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        cursor.execute('USE `'+target+'`')
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        try:
            if not exists:
                for table,ddl in definitions.items(): cursor.execute(ddl)
        finally:
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        conn.commit()
        assert comparable(snapshot(Database(target)))==comparable(definitions),'Copied schema differs from source'
        result={'source':source.options['database'],'newSchema':target,'tables':len(definitions),'copiedData':False,'structureMatchesSource':True}
        # Probe data exists only inside this transaction and is always rolled back.
        conn.start_transaction()
        try:
            cursor.execute("INSERT INTO Customer(fullName,email) VALUES('Relationship probe','relationship-probe@example.invalid')")
            customer=cursor.lastrowid
            result['customerWithoutAccountAllowed']=True
            cursor.execute("INSERT INTO Accounts(customerID,email,passwordHash,role) VALUES(%s,'first-probe@example.invalid','NOT_A_LOGIN_HASH','customer')",(customer,))
            result['firstAccountAllowed']=True
            try:
                cursor.execute("INSERT INTO Accounts(customerID,email,passwordHash,role) VALUES(%s,'second-probe@example.invalid','NOT_A_LOGIN_HASH','customer')",(customer,))
            except mysql.connector.IntegrityError as exc:
                assert exc.errno==1062
                result['secondAccountRejectedByUniqueCustomerID']=True
            else: raise AssertionError('More than one account was accepted for a customer')
            try:
                cursor.execute("INSERT INTO Accounts(customerID,email,passwordHash,role) VALUES(4294967295,'orphan-probe@example.invalid','NOT_A_LOGIN_HASH','customer')")
            except mysql.connector.IntegrityError as exc:
                assert exc.errno==1452
                result['accountWithoutExistingCustomerRejected']=True
            else: raise AssertionError('An orphan account was accepted')
        finally:
            conn.rollback()
        cursor.execute('SELECT COUNT(*) FROM Customer');assert cursor.fetchone()[0]==0
        cursor.execute('SELECT COUNT(*) FROM Accounts');assert cursor.fetchone()[0]==0
        result['probeDataRolledBack']=True
        result['relationship']='Each Customer has 0..1 Accounts; each Account belongs to exactly 1 Customer.'
        path=ROOT/'data/test_runs/relationship_review_schema.json'
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        cursor.close();conn.close()


if __name__=='__main__':main()
