import json
import math
from Model.application.errors import DomainError


class SearchQueryDAOImpl:
    def __init__(self, db):
        self.db = db

    def saveWithResults(self, customerID, queryType, criteria, query, results):
        if queryType not in {'text', 'voice', 'image'}:
            raise DomainError('Invalid query type')
        ids = [p['articleID'] for p in results]
        if len(ids) != len(set(ids)) or any(not math.isfinite(float(p.get('score', 0))) for p in results):
            raise DomainError('Invalid ranked results')
        with self.db.transaction() as c:
            queryID = self.db.query(
                'INSERT INTO SearchQuery(customerId,createdAt,searchCriteria) VALUES(%s,UTC_TIMESTAMP(),%s)',
                (customerID, json.dumps(criteria, ensure_ascii=False, default=str)), c)
            if queryType == 'text':
                self.db.query('INSERT INTO TextQuery(queryId,queryText) VALUES(%s,%s)',
                              (queryID, query['text']), c)
            elif queryType == 'voice':
                self.db.query('INSERT INTO VoiceQuery(queryId,audioReference,transcribedText) VALUES(%s,%s,%s)',
                              (queryID, query.get('audioReference') or '', query['text']), c)
            else:
                self.db.query('INSERT INTO ImageQuery(queryId,imageReference,selectedRegion) VALUES(%s,%s,%s)',
                              (queryID, query['imageReference'], json.dumps(query.get('region'), ensure_ascii=False)), c)
            for rank, product in enumerate(results, 1):
                self.db.query('INSERT INTO SearchResult(queryId,articleId,rank,score) VALUES(%s,%s,%s,%s)',
                              (queryID, product['articleID'], rank, float(product.get('score', 0))), c)
        return queryID

    def findById(self, queryID):
        return self.db.query('SELECT queryId AS queryID,customerId AS customerID,createdAt,searchCriteria '
                             'FROM SearchQuery WHERE queryId=%s', (queryID,), one=True)
