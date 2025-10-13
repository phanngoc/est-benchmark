# Project Management System

This document describes the project management functionality added to the estimation benchmark system.

## Overview

The project management system allows you to organize estimation runs and tasks into projects. Each project can contain multiple estimation runs, providing better organization and tracking of related estimations.

## Database Schema

### Projects Table

The `projects` table stores project information:

| Column | Type | Description |
|--------|------|-------------|
| `project_id` | TEXT (PK) | Unique project identifier |
| `name` | TEXT | Project name (required) |
| `description` | TEXT | Project description |
| `created_at` | TIMESTAMP | Creation timestamp (auto-generated) |
| `updated_at` | TIMESTAMP | Last update timestamp (auto-generated) |
| `status` | TEXT | Project status (default: 'active') |

**Valid Status Values:**
- `active` - Currently active project
- `completed` - Finished project
- `archived` - Archived project
- `on-hold` - Project on hold

### Updated Tables

#### estimation_runs Table
Added `project_id` as a foreign key:
```sql
FOREIGN KEY (project_id) REFERENCES projects(project_id)
```

#### estimation_tasks Table
Added `project_id` as a foreign key:
```sql
FOREIGN KEY (project_id) REFERENCES projects(project_id)
```

### Indexes

The following indexes are created for optimal query performance:
- `idx_projects_status` - On `projects(status)`
- `idx_estimation_runs_project_id` - On `estimation_runs(project_id)`
- `idx_estimation_tasks_project_id` - On `estimation_tasks(project_id)`

## ProjectManager Class

The `ProjectManager` class provides CRUD operations for projects.

### Initialization

```python
from utils.project_manager import get_project_manager

# Get singleton instance
pm = get_project_manager()

# Or with custom database path
pm = get_project_manager(db_path="./custom_db.db")
```

### CRUD Operations

#### Create Project

```python
project_id = pm.create_project(
    name="E-commerce Platform",
    description="Building a full-stack e-commerce platform",
    status="active",  # Optional, defaults to "active"
    project_id="custom_id"  # Optional, auto-generated if not provided
)
```

**Returns:** `project_id` (string)

**Raises:** `ValueError` if name is empty or project_id already exists

#### Get Project

```python
project = pm.get_project(project_id="proj_abc123")

if project:
    print(f"Name: {project['name']}")
    print(f"Status: {project['status']}")
    print(f"Created: {project['created_at']}")
```

**Returns:** Dictionary with project details or `None` if not found

#### Update Project

```python
success = pm.update_project(
    project_id="proj_abc123",
    name="Updated E-commerce Platform",  # Optional
    description="Updated description",    # Optional
    status="completed"                    # Optional
)
```

**Returns:** `True` if successful, `False` if project not found

**Note:** The `updated_at` timestamp is automatically updated.

#### Delete Project

```python
# Delete without cascade (fails if project has estimations)
success = pm.delete_project(project_id="proj_abc123", cascade=False)

# Delete with cascade (deletes all associated estimations and tasks)
success = pm.delete_project(project_id="proj_abc123", cascade=True)
```

**Parameters:**
- `project_id` - Project to delete
- `cascade` - If `True`, deletes associated estimation runs and tasks

**Returns:** `True` if successful, `False` if project not found

#### List Projects

```python
# List all projects
projects = pm.list_projects()

# List with filtering
projects = pm.list_projects(
    status="active",  # Optional status filter
    limit=50,         # Optional, defaults to 100
    offset=0          # Optional, for pagination
)

for project in projects:
    print(f"{project['name']} - {project['status']}")
```

**Returns:** List of project dictionaries

#### Search Projects

```python
# Search by keyword
projects = pm.search_projects(keyword="ecommerce")

# Search by status
projects = pm.search_projects(status="active")

# Combined search
projects = pm.search_projects(
    keyword="platform",
    status="active"
)
```

**Returns:** List of matching project dictionaries

**Note:** Keyword search looks in both `name` and `description` fields.

#### Get Project Statistics

```python
stats = pm.get_project_statistics(project_id="proj_abc123")

print(f"Total Estimations: {stats['total_estimations']}")
print(f"Total Tasks: {stats['total_tasks']}")
print(f"Total Effort: {stats['total_effort']} mandays")
print(f"Avg Confidence: {stats['avg_confidence']}")
```

**Returns:** Dictionary with project statistics

## Configuration

New project-related settings in `config.py`:

```python
class Config:
    # Project Management Configuration
    DEFAULT_PROJECT_STATUS = "active"
    PROJECT_STATUS_OPTIONS = ["active", "completed", "archived", "on-hold"]
    AUTO_CREATE_DEFAULT_PROJECT = True
    DEFAULT_PROJECT_NAME = "Default Project"
    DEFAULT_PROJECT_DESCRIPTION = "Default project for estimations without specific project assignment"
```

### Configuration Options

| Setting | Type | Description |
|---------|------|-------------|
| `DEFAULT_PROJECT_STATUS` | str | Default status for new projects |
| `PROJECT_STATUS_OPTIONS` | list | Valid project status values |
| `AUTO_CREATE_DEFAULT_PROJECT` | bool | Auto-create default project if none exists |
| `DEFAULT_PROJECT_NAME` | str | Name for auto-created default project |
| `DEFAULT_PROJECT_DESCRIPTION` | str | Description for auto-created default project |

## Usage Examples

### Example 1: Creating and Managing Projects

```python
from utils.project_manager import get_project_manager

pm = get_project_manager()

# Create a new project
project_id = pm.create_project(
    name="CRM System",
    description="Customer Relationship Management system for sales team",
    status="active"
)

# Get project details
project = pm.get_project(project_id)
print(f"Created project: {project['name']}")

# Update project status
pm.update_project(project_id, status="completed")

# Get project statistics
stats = pm.get_project_statistics(project_id)
print(f"Total effort: {stats['total_effort']} mandays")
```

### Example 2: Listing and Searching Projects

```python
from utils.project_manager import get_project_manager

pm = get_project_manager()

# List all active projects
active_projects = pm.list_projects(status="active")
print(f"Found {len(active_projects)} active projects")

# Search for projects
results = pm.search_projects(keyword="platform")
for project in results:
    print(f"- {project['name']}: {project['description']}")
```

### Example 3: Integrating with Estimation Workflow

```python
from utils.project_manager import get_project_manager
from utils.estimation_result_tracker import get_result_tracker

# Create project
pm = get_project_manager()
project_id = pm.create_project(
    name="Mobile App Development",
    description="iOS and Android app for fitness tracking"
)

# Create estimation run with project reference
tracker = get_result_tracker()
estimation_id = tracker.create_estimation_run(
    estimation_id="est_20231013_001",
    file_path="./exports/fitness_app_estimation.xlsx",
    summary_data={
        "project_id": project_id,  # Link to project
        "total_effort": 45.5,
        "total_tasks": 28,
        "average_confidence": 0.82,
        "workflow_status": "completed",
        "project_description": "Fitness tracking mobile application"
    }
)

# Get project statistics
stats = pm.get_project_statistics(project_id)
print(f"Project has {stats['total_estimations']} estimation runs")
```

## Testing

A test script is provided to verify all CRUD operations:

```bash
python test_project_manager.py
```

This will test:
1. Creating projects
2. Retrieving project details
3. Updating projects
4. Listing projects
5. Searching projects
6. Getting project statistics
7. Deleting projects

## Migration Notes

### For Existing Databases

If you have an existing `estimation_tracker.db` database:

1. **Backup your database:**
   ```bash
   cp estimation_tracker.db estimation_tracker.db.backup
   ```

2. **Option A - Manual Migration:**
   The new tables and columns will be created automatically when you initialize the `EstimationResultTracker`. Existing data will remain intact.

3. **Option B - Fresh Start:**
   If you want to start fresh with the new schema:
   ```bash
   rm estimation_tracker.db
   ```
   The database will be recreated with the new schema on next use.

### Updating Existing Code

If you have code that creates estimation runs, you can now optionally include a `project_id`:

```python
# Before
tracker.create_estimation_run(
    estimation_id="est_001",
    file_path="./export.xlsx",
    summary_data={...}
)

# After (with project support)
tracker.create_estimation_run(
    estimation_id="est_001",
    file_path="./export.xlsx",
    summary_data={
        "project_id": "proj_abc123",  # New optional field
        ...
    }
)
```

## Best Practices

1. **Organize by Project:** Group related estimations under a project for better tracking
2. **Use Meaningful Names:** Give projects descriptive names that clearly identify their purpose
3. **Update Status:** Keep project status up-to-date (active → completed → archived)
4. **Check Statistics:** Use `get_project_statistics()` to monitor project progress
5. **Cascade Carefully:** When deleting projects with `cascade=True`, ensure you really want to delete all associated data

## Logging

The `ProjectManager` uses the application's logging system. Key events logged:

- Project creation
- Project updates
- Project deletion (including cascade deletions)
- Search operations
- Statistics queries

Log level can be configured in `config.py`.

## Error Handling

The `ProjectManager` includes comprehensive error handling:

- **ValueError:** Raised when required parameters are missing or invalid
- **sqlite3.IntegrityError:** Handled for duplicate project IDs
- **General Exceptions:** Logged with rollback on database operations

Always wrap operations in try-except blocks when appropriate:

```python
try:
    project_id = pm.create_project(name="My Project")
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```
