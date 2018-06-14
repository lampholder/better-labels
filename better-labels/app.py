# app.py

import os
import json
import uuid

import boto3

from flask import Flask, jsonify, request
app = Flask(__name__)

"""
What does this thing look like?

GET     mount/lampholder/concorde/issues/1234/labels

{
    'labels': [
        {
            'id': 'uuid-uuid-uuid-uuid-uuid-uuid',
            'name': 'bug',
            'uri': 'mount/labels/uuid-uuid-uuid-uuid-uuid-uuid',
            'fields': {
                'color': '#FFAB23',
                'type': 'defect'
            }
        },
        {
            'id': 'uuid-uuid-uuid-uuid-uuid-uuid',
            'name': 'maintenance',
            'uri': 'mount/labels/uuid-uuid-uuid-uuid-uuid-uuid',
            'fields': {
                'color': '#FFAB23',
                'type': 'maintenance'
            }
        },
    ]
}

GET     mount/lampholder/concorde/issues/1234/labels/uuid-uuid-uuid-uuid-uuid-uuid

{
    'id': 'uuid-uuid-uuid-uuid-uuid-uuid',
    'name': 'bug',
    'fields': {
        'color': '#FFAB23',
        'type': 'defect'
    }
}

GET     mount/labels/uuid-uuid-uuid-uuid-uuid-uuid

{
    'id': 'uuid-uuid-uuid-uuid-uuid-uuid',
    'name': 'bug',
    'fields': {
        'color': '#FFAB23',
        'type': 'defect'
    }
}

"""

"""

1.1 GET    mount/labels
        -> Return the full representation of all the labels

1.2 PUT    mount/labels/<uuid>
        -> (Over)write a representation of a label with the specified uuid

1.3 GET    mount/labels/<uuid>
        -> Return the full representation of a single label

1.4 POST   mount/labels
        -> Write a representation of a label with a system-provided uuid

1.5 DELETE mount/labels/<uuid>
        -> Delete the label with the specified uuid

1.6 DELETE mount/labels [NOT IMPLEMENTED]
        -> Delete all the labels

1.7 PUT    mount/labels
        -> Replace all of the labels with a fresh representation


2.1 GET    mount/lampholder/concorde/issues/1234/labels
        -> Return the full json representation of the indicated label

2.2 PUT    mount/lampholder/concorde/issues/1234/labels
        -> Submit a list of label ids that will replace the existing list [NOT
           IMPLEMENTED]

2.3 POST   mount/lampholder/concorde/issues/1234/labels
        -> Submit a list of label ids that will add to the existing list

2.4 DELETE mount/lampholder/concorde/issues/1234/labels
        -> Delete all of the labels associated with an issue

2.5 DELETE mount/lampholder/concorde/issues/1234/labels/<uuid>
        -> Delete just that one label from the issue's list

2.6 PATCH  mount/lampholder/concorde/issues/1234/labels
        -> Add all of the labels specified (by id) in addLabelIds, then
           delete all of the labels specified (by id) in removelabelIds

"""





class DAO:
    """
    This DAO object is responsible for:
        - managing all the connections to the db
        - marshalling dynamodb objects into standard python objects

    As a general rule, every non-get methods should return their id.
    """

    ISSUES_TABLE = os.environ['ISSUES_TABLE'] if 'ISSUES_TABLE' in os.environ else 'issues-table-dev'
    LABELS_TABLE = os.environ['LABELS_TABLE'] if 'LABELS_TABLE' in os.environ else 'labels-table-dev'

    def __init__(self, url_stem, region='us-east-1'):
        self._url_stem = url_stem
        self._client = boto3.client('dynamodb', region_name = region)


    def _item_to_label(self, item):
        return {
            'id': item.get('id').get('S'),
            'name': item.get('name').get('S'),
            # 'location': self._url_stem + '/labels/' + item.get('id').get('S'),
            'fields': json.loads(item.get('fields').get('S'))
        }

    def _item_to_issue(self, item):
        return {
            'path': item.get('path').get('S'),
            'labelIds': item.get('labelIds').get('SS')
        }

    def get_labels(self):
        """Returns fully-hydrated label objects"""
        resp = self._client.scan(TableName=self.LABELS_TABLE)
        return [self._item_to_label(item) for item in resp['Items']]


    def get_label(self, id):
        resp = self._client.get_item(
            TableName=self.LABELS_TABLE,
            Key={
                'id': {'S': id}
            }
        )

        if 'Item' not in resp:
            return None

        return self._item_to_label(resp['Item'])

    """
    {
        'id': 'uuid-uuid-uuid-uuid-uuid-uuid',
        'name': 'bug',
        'location': 'https://example.com/labels/uuid-uuid-uuid-uuid-uuid-uuid',
        # location is generated, not stored
        'fields': {
            'color': '#FFAB23',
            'type': 'defect'
        }
    }
    """
    def set_label(self, id, name, fields):
        label = {
            'id': {'S': id},
            'name': {'S': name},
            'fields': {'S': json.dumps(fields)}
        }

        self._client.put_item(
            TableName=self.LABELS_TABLE,
            Item=label
        )

        return id

    def delete_all_labels(self):
        """
        FIXME: This is not the right way to do this
        """
        labels = self.get_labels()
        for label in labels:
            self.delete_label(label['id'])

    def delete_label(self, id):
        self._client.delete_item(
            TableName=self.LABELS_TABLE,
            Key={
                'id': {'S': id}
            }
        )

        return id


    def get_issue_labels(self, issue_path):
        label_ids = self.get_issue_label_ids(issue_path)

        return {
            'path': issue_path,
            # 'location': self._url_stem + '/' + issue_path + '/labels',
            'labels': [label for label in [self.get_label(label_id) for label_id in
                                           label_ids]
                       if label is not None]
        }


    def get_issue_label_ids(self, issue_path):
        resp = self._client.get_item(
            TableName=self.ISSUES_TABLE,
            Key={
                'path': {'S': issue_path}
            }
        )

        if 'Item' not in resp:
            return []

        item = resp['Item']
        return item['labelIds']['SS'] if 'labelIds' in item else []


    def set_issue_label_ids(self, issue_path, label_ids):
        item = {
            'path': {'S': issue_path}
        }

        real_label_ids = [label['id'] for label in self.get_labels()]

        new_label_ids = [label_id for label_id in label_ids
                         if label_id in real_label_ids]

        if len(new_label_ids) > 0:
            item['labelIds'] = {'SS': list(set(new_label_ids))}

        put = self._client.put_item(
            TableName=self.ISSUES_TABLE,
            Item=item
        )

        return issue_path

    def search(self, search_criteria):
        labels = dao.get_labels()
        matching_label_ids = [label['id'] for label in labels
                              if search_criteria in label['fields']
                              or search_criteria in label['name']]

        scan = self._client.scan(TableName=self.ISSUES_TABLE)

        if 'Items' not in scan:
            return []

        issues = [self._item_to_issue(item) for item in scan['Items']]
        print(json.dumps(issues, indent=2))

        matching_issues = [issue for issue in issues
                           if
                           len(set(issue['labelIds']).intersection(matching_label_ids))
                           > 0]

        issue_numbers = [issue['path'].split('/')[-1]
                         for issue in matching_issues]

        github_url = 'https://github.com/vector-im/riot-web/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+'

        return github_url + '+'.join(issue_numbers)


dao = DAO(url_stem='https://localhost:5000')

# Convenience methods:

def if_found(value):
    if value:
        return jsonify(value)
    else:
        return jsonify({'error': 'Not found'}), 404


def rehydrate_labels(label_ids):
    return [dao.get_label(label_id) for label_id in label_ids]


# Routed methods:

@app.route('/labels', methods=['GET'])
def get_labels():
    """
    1.1 GET    mount/labels
            -> Return the full representation of all the labels
    """
    return if_found(dao.get_labels())

@app.route('/labels/<string:id>', methods=['PUT'])
def put_label(id):
    """
    1.2 PUT    mount/labels/<uuid>
            -> (Over)write a representation of a label with the specified uuid
    """
    label_id = dao.set_label(id=id,
                             name=request.json['name'],
                             fields=request.json['fields'])

    return jsonify(dao.get_label(label_id))

@app.route('/labels', methods=['PUT'])
def put_labels():
    """
    1.7 PUT    mount/labels
            -> Replace all of the labels with a fresh representation
    """
    dao.delete_all_labels()
    for label in request.json:
        if 'id' not in label or not label['id']:
            label['id'] = str(uuid.uuid4())
        dao.set_label(id=label['id'],
                      name=label['name'],
                      fields=label['fields'])
    return if_found(dao.get_labels())

@app.route('/labels/<string:id>', methods=['GET'])
def get_label(id):
    """
    1.3 GET    mount/labels/<uuid>
            -> Return the full representation of a single label
    """
    return if_found(dao.get_label(id))

@app.route('/labels', methods=['POST'])
def post_label():
    """
    1.4 POST   mount/labels
            -> Write a representation of a label with a system-provided uuid
    """
    label_id = dao.set_label(id=str(uuid.uuid4()),
                             name=request.json['name'],
                             fields=request.json['fields'])

    return jsonify(dao.get_label(label_id))

@app.route('/labels/<string:id>', methods=['DELETE'])
def delete_label(id):
    """
    1.5 DELETE mount/labels/<uuid>
            -> Delete the label with the specified uuid
    """
    dao.delete_label(id)
    return jsonify(dao.get_label(id))


@app.route('/<string:repo>/<string:project>/issues/<int:issue_number>/labels',
           methods=['GET'])
def get_issue_labels(repo, project, issue_number):
    """
    2.1 GET    mount/lampholder/concorde/issues/1234/labels
            -> Return the full json representation of the indicated label
    """
    issue_path = '%s/%s/issues/%d' % (repo, project, issue_number)

    return jsonify(dao.get_issue_labels(issue_path))

@app.route('/<string:repo>/<string:project>/issues/<int:issue_number>/labels',
           methods=['POST'])
def post_issue_labels(repo, project, issue_number):
    """
    2.3 POST   mount/lampholder/concorde/issues/1234/labels
            -> Submit a list of label ids that will add to the existing list
    """
    issue_path = '%s/%s/issues/%d' % (repo, project, issue_number)

    new_label_ids = request.json

    current_label_ids = dao.get_issue_label_ids(issue_path)

    revised_label_ids = current_label_ids + new_label_ids

    dao.set_issue_label_ids(issue_path, revised_label_ids)

    return if_found(dao.get_issue_labels(issue_path))

@app.route('/<string:repo>/<string:project>/issues/<int:issue_number>/labels/<string:delete_label_id>',
           methods=['DELETE'])
def delete_issue_label(repo, project, issue_number, delete_label_id):
    """
    2.5 DELETE mount/lampholder/concorde/issues/1234/labels/<uuid>
            -> Delete just that one label from the issue's list
    """
    issue_path = '%s/%s/issues/%d' % (repo, project, issue_number)

    current_label_ids = dao.get_issue_label_ids(issue_path)

    revised_label_ids = [label_id for label_id in current_label_ids
                         if label_id != delete_label_id]

    dao.set_issue_label_ids(issue_path, revised_label_ids)

    return if_found(dao.get_issue_labels(issue_path))

@app.route('/<string:repo>/<string:project>/issues/<int:issue_number>/labels',
           methods=['PATCH'])
def patch_issue_labels(repo, project, issue_number):
    """
    2.6 PATCH  mount/lampholder/concorde/issues/1234/labels
            -> Add all of the labels specified (by id) in addLabelIds, then
               delete all of the labels specified (by id) in removelabelIds
    """
    add_label_ids = request.json.get('addLabelIds') or []
    remove_label_ids = request.json.get('removeLabelIds') or []

    issue_path = '%s/%s/issues/%d' % (repo, project, issue_number)

    current_label_ids = dao.get_issue_label_ids(issue_path)

    revised_label_ids = [label_id for label_id in current_label_ids + add_label_ids
                         if label_id not in remove_label_ids]

    dao.set_issue_label_ids(issue_path, revised_label_ids)

    return if_found(dao.get_issue_labels(issue_path))

@app.route('/search', methods=['GET'])
def search():
    return jsonify(dao.search(request.args.get('query')))

if __name__ == "__main__":
    app.run()
