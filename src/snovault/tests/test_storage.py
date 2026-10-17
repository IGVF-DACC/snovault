import pytest
pytestmark = pytest.mark.storage


def test_storage_creation(session):
    from snovault.storage import (
        PropertySheet,
        CurrentPropertySheet,
        TransactionRecord,
        Blob,
        Key,
        Link,
    )
    assert session.query(PropertySheet).count() == 0
    assert session.query(CurrentPropertySheet).count() == 0
    assert session.query(TransactionRecord).count() == 0
    assert session.query(Blob).count() == 0
    assert session.query(Key).count() == 0
    assert session.query(Link).count() == 0


def test_transaction_record(session):
    from snovault.storage import (
        Resource,
        PropertySheet,
        TransactionRecord,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item')
    session.add(resource)
    propsheet = PropertySheet(name=name, properties=props1, rid=resource.rid)
    session.add(propsheet)
    session.flush()
    assert session.query(PropertySheet).count() == 1
    propsheet = session.query(PropertySheet).one()
    assert session.query(TransactionRecord).count() == 1
    record = session.query(TransactionRecord).one()
    assert record.tid
    assert propsheet.tid == record.tid


def test_transaction_record_rollback(session):
    import transaction
    import uuid
    from snovault.storage import Resource
    rid = uuid.uuid4()
    resource = Resource('test_item', {'': {}}, rid=rid)
    session.add(resource)
    transaction.commit()
    transaction.begin()
    sp = session.begin_nested()
    resource = Resource('test_item', {'': {}}, rid=rid)
    session.add(resource)
    with pytest.raises(Exception):
        sp.commit()
    sp.rollback()
    resource = Resource('test_item', {'': {}})
    session.add(resource)
    transaction.commit()


def test_current_propsheet(session):
    from snovault.storage import (
        CurrentPropertySheet,
        Resource,
        PropertySheet,
        TransactionRecord,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item', {name: props1})
    session.add(resource)
    session.flush()
    resource = session.query(Resource).one()
    assert resource.rid
    assert resource[name] == props1
    propsheet = session.query(PropertySheet).one()
    assert propsheet.sid
    assert propsheet.rid == resource.rid
    current = session.query(CurrentPropertySheet).one()
    assert current.sid == propsheet.sid
    assert current.rid == resource.rid
    record = session.query(TransactionRecord).one()
    assert record.tid
    assert propsheet.tid == record.tid


def test_current_propsheet_update(session):
    from snovault.storage import (
        CurrentPropertySheet,
        Resource,
        PropertySheet,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item', {name: props1})
    session.add(resource)
    session.flush()
    resource = session.query(Resource).one()
    props2 = {'foo': 'baz'}
    resource[name] = props2
    session.flush()
    resource = session.query(Resource).one()
    session.flush()
    assert resource[name] == props2
    assert session.query(PropertySheet).count() == 2
    assert [propsheet.properties for propsheet in resource.data[name].history] == [props1, props2]
    current = session.query(CurrentPropertySheet).one()
    assert current.sid


def test_delete_simple(session, storage):
    from snovault.storage import (
        Resource,
        Key,
        PropertySheet,
        CurrentPropertySheet,
        TransactionRecord,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item', {name: props1})
    session.add(resource)
    session.flush()
    resource = session.query(Resource).one()
    check = storage.get_by_uuid(str(resource.rid))
    assert check[name] == props1
    # add a key
    testname = 'foo'
    key = Key(rid=resource.rid, name=testname, value=props1[testname])
    session.add(key)
    session.flush()
    assert session.query(Key).count() == 1

    propsheet = session.query(PropertySheet).one()
    assert propsheet.sid
    assert propsheet.rid == resource.rid
    current = session.query(CurrentPropertySheet).one()
    assert current.sid == propsheet.sid
    assert current.rid == resource.rid

    storage.delete_by_uuid(str(resource.rid))
    check_post = storage.get_by_uuid(str(resource.rid))
    assert not check_post
    assert session.query(Key).count() == 0
    assert session.query(PropertySheet).count() == 0
    assert session.query(CurrentPropertySheet).count() == 0


def test_delete_compound(session, storage):
    from snovault.storage import (
        CurrentPropertySheet,
        Resource,
        PropertySheet,
        Key,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item', {name: props1})
    session.add(resource)
    session.flush()
    resource = session.query(Resource).one()
    check = storage.get_by_uuid(str(resource.rid))
    assert check[name] == props1
    # add a key
    testname = 'foo'
    key = Key(rid=resource.rid, name=testname, value=props1[testname])
    session.add(key)
    session.flush()
    assert session.query(Key).count() == 1

    props2 = {'foo': 'baz'}
    resource[name] = props2
    session.flush()
    resource = session.query(Resource).one()
    session.flush()
    assert resource[name] == props2
    assert session.query(PropertySheet).count() == 2
    assert [propsheet.properties for propsheet in resource.data[name].history] == [props1, props2]
    current = session.query(CurrentPropertySheet).one()
    assert current.sid

    storage.delete_by_uuid(str(resource.rid))
    check_post = storage.get_by_uuid(str(resource.rid))
    assert not check_post
    assert session.query(Key).count() == 0
    assert session.query(PropertySheet).count() == 0
    assert session.query(CurrentPropertySheet).count() == 0


def test_keys(session):
    from sqlalchemy.orm.exc import FlushError
    from snovault.storage import (
        Resource,
        Key,
    )
    name = 'testdata'
    props1 = {'foo': 'bar'}
    resource = Resource('test_item', {name: props1})
    session.add(resource)
    session.flush()
    resource = session.query(Resource).one()

    testname = 'foo'
    key = Key(rid=resource.rid, name=testname, value=props1[testname])
    session.add(key)
    session.flush()
    assert session.query(Key).count() == 1
    othertest = 'foofoo'
    othervalue = 'barbar'
    key2 = Key(rid=resource.rid, name=othertest, value=othervalue)
    session.add(key2)
    session.flush()
    assert session.query(Key).count() == 2
    props2 = {'foofoo': 'barbar'}
    resource2 = Resource('test_item', {name: props2})
    session.add(resource2)
    session.flush()
    key3 = Key(rid=resource2.rid, name=testname, value=props1[testname])
    session.add(key3)
    with pytest.raises(FlushError):
        session.flush()


def test_get_by_uuids(session, storage):
    import uuid
    from snovault.storage import Resource
    resources = [Resource('test_item', {'': {'foo': str(i)}}) for i in range(3)]
    session.add_all(resources)
    session.flush()
    rids = [resource.rid for resource in resources]
    missing = uuid.uuid4()
    models = storage.get_by_uuids([str(rids[2]), str(missing), rids[0]])
    assert [model.rid if model else None for model in models] == [rids[2], None, rids[0]]
    assert storage.get_by_uuids([]) == []


def test_get_by_unique_keys(session, storage):
    from snovault.storage import Key, Resource
    resources = {}
    for value in ('a', 'b'):
        resource = Resource('test_item', {'': {'foo': value}})
        session.add(resource)
        session.flush()
        session.add(Key(rid=resource.rid, name='foo', value=value))
        resources[value] = resource
    session.flush()
    models = storage.get_by_unique_keys('foo', ['b', 'missing', 'a'])
    assert [model.rid if model else None for model in models] == [
        resources['b'].rid, None, resources['a'].rid,
    ]
    assert storage.get_by_unique_keys('other', ['a']) == [None]
    assert storage.get_by_unique_keys('foo', []) == []


def test_get_incoming_links_matches_get_rev_links(session, storage):
    from snovault.storage import Link, Resource
    target = Resource('target_type', {'': {}})
    sources = [Resource('type_a', {'': {}}), Resource('type_a', {'': {}}), Resource('type_b', {'': {}})]
    other = Resource('type_a', {'': {}})
    session.add_all([target, other] + sources)
    session.flush()
    for source in sources:
        session.add(Link(source_rid=source.rid, rel='parent', target_rid=target.rid))
    session.add(Link(source_rid=other.rid, rel='other_rel', target_rid=target.rid))
    session.flush()
    session.expire_all()
    model = storage.get_by_uuid(str(target.rid))
    rows = storage.get_incoming_links(model)
    assert sorted((rel, str(source), item_type) for rel, source, item_type in rows) == sorted(
        [('parent', str(source.rid), source.item_type) for source in sources]
        + [('other_rel', str(other.rid), 'type_a')]
    )
    for item_types in ((), ('type_a',), ('type_b',), ('type_a', 'type_b'), ('missing',)):
        expected = storage.get_rev_links(model, 'parent', *item_types)
        actual = [
            source for rel, source, item_type in rows
            if rel == 'parent' and (not item_types or item_type in item_types)
        ]
        assert sorted(map(str, actual)) == sorted(map(str, expected))


def test_get_incoming_links_batch_matches_single_item_query(session, storage):
    from snovault.storage import Link, Resource
    first = Resource('target_type', {'': {}})
    second = Resource('target_type', {'': {}})
    unlinked = Resource('target_type', {'': {}})
    sources = [Resource('type_a', {'': {}}), Resource('type_b', {'': {}}), Resource('type_a', {'': {}})]
    session.add_all([first, second, unlinked] + sources)
    session.flush()
    session.add(Link(source_rid=sources[0].rid, rel='parent', target_rid=first.rid))
    session.add(Link(source_rid=sources[1].rid, rel='other', target_rid=first.rid))
    session.add(Link(source_rid=sources[2].rid, rel='parent', target_rid=second.rid))
    session.flush()
    session.expire_all()
    models = [storage.get_by_uuid(str(resource.rid)) for resource in (first, second, unlinked)]
    batch = storage.get_incoming_links_batch(models)
    assert set(batch) == {first.rid, second.rid, unlinked.rid}
    assert batch[unlinked.rid] == []
    for model in models:
        assert sorted(batch[model.rid]) == sorted(storage.get_incoming_links(model))
    assert storage.get_incoming_links_batch([]) == {}


def test_S3BlobStorage_boto3(mocker):
    from snovault.storage import S3BlobStorage
    mocker.patch('boto3.Session.resource')
    mocker.patch('boto3.Session.client')
    bucket = 'test'
    mock_key = mocker.Mock()
    storage = S3BlobStorage(bucket)
    storage.bucket.name = bucket
    storage.store_conn.return_value = mock_key
    download_meta = {'blob_id': '123'}
    storage.store_blob('data', download_meta)
    assert download_meta['bucket'] == 'test'
    assert 'key' in download_meta
    assert storage.store_conn.put_object.call_count == 1
    storage.read_conn.return_value = mock_key
    storage.read_conn.get_object()['Body'].read.return_value = 'data'
    data = storage.get_blob(download_meta)
    assert data == 'data'
    assert storage.read_conn.get_object.call_count == 2


def test_S3BlobStorage_boto3_with_header(mocker):
    from snovault.storage import S3BlobStorage
    mocker.patch('boto3.Session.resource')
    mocker.patch('boto3.Session.client')
    bucket = 'test'
    mock_key = mocker.Mock()
    storage = S3BlobStorage(bucket)
    storage.bucket.name = bucket
    storage.store_conn.return_value = mock_key
    download_meta = {'blob_id': '123', 'type': 'text/plain'}
    storage.store_blob('data', download_meta)
    assert 'type' in download_meta
    assert download_meta['type'] == 'text/plain'


def test_S3BlobStorage_boto3_get_blob_url_for_s3_file(mocker):
    from snovault.storage import S3BlobStorage
    mocker.patch('boto3.Session.resource')
    mocker.patch('boto3.Session.client')
    bucket = 'test'
    storage = S3BlobStorage(bucket)
    storage.bucket.name = bucket
    download_meta = {'blob_id': '123'}
    storage.read_conn.generate_presigned_url.return_value = 'http://testurl'
    url = storage.get_blob_url(download_meta)
    assert url == 'http://testurl'
    storage.read_conn.generate_presigned_url.assert_called_once_with(
        Params={'Key': '123', 'Bucket': 'test'}, ExpiresIn=129600, ClientMethod='get_object'
    )
