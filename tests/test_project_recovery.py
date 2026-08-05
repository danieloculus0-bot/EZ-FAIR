from project_store import ProjectMetadata, ProjectRecord, ProjectStore


def test_project_backup_and_recovery(tmp_path):
    store = ProjectStore(tmp_path / "projects.db", tmp_path / "backups")
    project = ProjectRecord(name="First", metadata=ProjectMetadata(drawing_no="A100"))
    store.save(project)
    project.name = "Changed"
    store.save(project)

    history = store.backup_history(project.id)
    assert len(history) == 2
    assert history[0].suffix == ".json"

    recovered = store.recover_latest(project.id)
    assert recovered.id == project.id
    assert recovered.name == "Changed"
    assert store.load(project.id).name == "Changed"


def test_backup_retention(tmp_path):
    store = ProjectStore(tmp_path / "projects.db", tmp_path / "backups")
    project = ProjectRecord(name="Retention")
    for index in range(25):
        project.status = str(index)
        store.save(project)
    assert len(store.backup_history(project.id)) <= 20
