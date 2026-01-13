# Environment Management Subagent Test Prompts

## Basic Environment Operations

### 1. Create a New Environment
```
Create a new Cyoda environment called "staging" for testing purposes.
```

### 2. List All Environments
```
Show me all the Cyoda environments I have access to.
```

### 3. Describe an Environment
```
Describe the "production" environment and show what services are running in it.
```

### 4. Get Environment Status
```
What is the current status of the "development" environment?
```

## Deployment Operations

### 5. Deploy Application to Environment
```
Deploy my application to the staging environment. The application is located at /path/to/my-app.
```

### 6. Check Deployment Status
```
Check the deployment status of my application in the production environment.
```

### 7. Rollback Deployment
```
Rollback the last deployment in the staging environment.
```

## Credentials and Access Management

### 8. Issue Technical User Credentials
```
Issue technical user credentials for the staging environment so I can access it programmatically.
```

### 9. List Environment Users
```
Who has access to the production environment?
```

### 10. Revoke User Access
```
Remove user john@example.com from the staging environment.
```

## Configuration and Settings

### 11. Update Environment Configuration
```
Update the environment variables for the development environment. Set DATABASE_URL to "postgresql://localhost:5432/mydb".
```

### 12. Get Environment Configuration
```
Show me the current configuration for the staging environment.
```

### 13. Enable/Disable Features
```
Enable the new feature flag "beta_features" in the development environment.
```

## Monitoring and Logs

### 14. View Environment Logs
```
Show me the recent logs from the production environment.
```

### 15. Monitor Resource Usage
```
What is the current CPU and memory usage in the staging environment?
```

### 16. Get Performance Metrics
```
Show me the performance metrics for the last 24 hours in the production environment.
```

## Troubleshooting

### 17. Diagnose Environment Issues
```
The staging environment seems to be running slowly. Can you diagnose what might be wrong?
```

### 18. Check Service Health
```
Are all services healthy in the production environment?
```

### 19. View Error Logs
```
Show me any errors that occurred in the development environment in the last hour.
```

## Advanced Operations

### 20. Scale Environment Resources
```
Scale up the production environment to handle more traffic. Increase the number of replicas to 5.
```

### 21. Backup Environment
```
Create a backup of the staging environment before we deploy the new version.
```

### 22. Restore from Backup
```
Restore the production environment from the backup created on 2025-12-08.
```

## Multi-Environment Management

### 23. Compare Environments
```
Compare the configurations of the development and staging environments.
```

### 24. Sync Environments
```
Sync the configuration from production to staging environment.
```

### 25. Environment Promotion
```
Promote the application from staging to production after testing.
```
