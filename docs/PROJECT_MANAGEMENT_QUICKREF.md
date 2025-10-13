# Project Management Quick Reference

## Import

```python
from utils.project_manager import get_project_manager
pm = get_project_manager()
```

## Common Operations

### Create Project
```python
project_id = pm.create_project(
    name="My Project",
    description="Project description",
    status="active"  # active, completed, archived, on-hold
)
```

### Get Project
```python
project = pm.get_project(project_id)
```

### Update Project
```python
pm.update_project(
    project_id,
    name="Updated Name",
    status="completed"
)
```

### List Projects
```python
# All projects
projects = pm.list_projects()

# Active projects only
active = pm.list_projects(status="active")

# With pagination
projects = pm.list_projects(limit=20, offset=0)
```

### Search Projects
```python
# By keyword
results = pm.search_projects(keyword="ecommerce")

# By status
results = pm.search_projects(status="active")

# Both
results = pm.search_projects(keyword="app", status="active")
```

### Get Statistics
```python
stats = pm.get_project_statistics(project_id)
# Returns: total_estimations, total_tasks, total_effort, avg_confidence
```

### Delete Project
```python
# Without cascade (fails if has estimations)
pm.delete_project(project_id, cascade=False)

# With cascade (deletes all associated data)
pm.delete_project(project_id, cascade=True)
```

## Database Schema

### projects table
- `project_id` (TEXT, PK)
- `name` (TEXT, NOT NULL)
- `description` (TEXT)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `status` (TEXT, default='active')

### Updated tables
- `estimation_runs.project_id` (FK → projects)
- `estimation_tasks.project_id` (FK → projects)

## Configuration (config.py)

```python
DEFAULT_PROJECT_STATUS = "active"
PROJECT_STATUS_OPTIONS = ["active", "completed", "archived", "on-hold"]
AUTO_CREATE_DEFAULT_PROJECT = True
DEFAULT_PROJECT_NAME = "Default Project"
```

## Testing

```bash
python test_project_manager.py
```

## Full Documentation

See `docs/PROJECT_MANAGEMENT.md` for complete documentation.
