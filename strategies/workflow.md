Here’s an updated and more detailed workflow that covers various development scenarios, including model and schema changes, Flask app code updates, dependency installations, and database content changes. It also outlines the process for testing the app on Heroku's front end.

---

### **Comprehensive Development Workflow:**

This guide explains how to handle different development tasks in a Flask app with PostgreSQL. We will cover these situations:
1. **Developer updates models and schema**
2. **Developer updates only Flask app code**
3. **Developer installs new dependencies**
4. **Developer modifies local database contents (adds/deletes users, etc.)**
5. **Testing front-end code on Heroku**

Each scenario involves development locally on the `development` branch and deployment to Heroku via the `stable-versions` branch.

---

### **1. Developer Updates Models and Schema**

When you modify the database schema (e.g., add new fields, models, or relationships):

#### **Step 1: Modify Models Locally**
- Update your models in the Flask app to reflect the new schema.

#### **Step 2: Create and Apply Migration Locally**
- Generate and apply Alembic migration:
   ```bash
   alembic revision --autogenerate -m "Update schema"
   alembic upgrade head
   ```
- This updates your local PostgreSQL database schema.

#### **Step 3: Commit and Push to `development` Branch**
- Commit your changes (including migration files) and push to the `development` branch:
   ```bash
   git add .
   git commit -m "Update models and apply migrations"
   git push origin development
   ```

#### **Step 4: Merge `development` into `stable-versions`**
- Merge `development` into `stable-versions`:
   ```bash
   git checkout stable-versions
   git merge development
   git push origin stable-versions
   ```

#### **Step 5: Apply Migrations on Heroku**
- Apply the migrations on Heroku:
   ```bash
   heroku run alembic upgrade head --app ws-companion
   ```

#### **Step 6: Sync Local Database to Heroku (Optional)**
- If you want to ensure that your local data matches Heroku, you can run the database sync with `truncate`:
   ```bash
   pgsync
   ```

---

### **2. Developer Updates Only Flask App Code**

When you modify the Flask app code (but not the database schema):

#### **Step 1: Make Code Changes Locally**
- Make the necessary updates to your Flask app (e.g., route changes, adding new features).

#### **Step 2: Commit and Push to `development` Branch**
- Commit your changes to the `development` branch:
   ```bash
   git add .
   git commit -m "Update Flask app code"
   git push origin development
   ```

#### **Step 3: Merge `development` into `stable-versions`**
- Merge `development` into `stable-versions`:
   ```bash
   git checkout stable-versions
   git merge development
   git push origin stable-versions
   ```

#### **Step 4: Heroku Deployment**
- Heroku will automatically deploy the changes from the `stable-versions` branch.

---

### **3. Developer Installs New Dependencies**

When new dependencies (e.g., Flask extensions, Python libraries) are added to the project:

#### **Step 1: Install New Dependencies Locally**
- Install the new dependencies using `pip`:
   ```bash
   pip install <new_dependency>
   ```

#### **Step 2: Update `requirements.txt`**
- Update the `requirements.txt` file with the new dependencies:
   ```bash
   pip freeze > requirements.txt
   ```

#### **Step 3: Commit and Push to `development` Branch**
- Commit the updated `requirements.txt` to the `development` branch:
   ```bash
   git add requirements.txt
   git commit -m "Add new dependencies"
   git push origin development
   ```

#### **Step 4: Merge `development` into `stable-versions`**
- Merge `development` into `stable-versions`:
   ```bash
   git checkout stable-versions
   git merge development
   git push origin stable-versions
   ```

#### **Step 5: Install Dependencies on Heroku**
- Heroku automatically installs new dependencies from the updated `requirements.txt` during the next deployment.

---

### **4. Developer Modifies Local Database Contents (Adds/Deletes Users, etc.)**

When you add or delete users or modify database contents (without changing the schema):

#### **Step 1: Modify Database Locally**
- Modify the database by adding/deleting users or updating contents via the app, admin interface, or `psql`.

#### **Step 2: Sync Local Database to Heroku with Truncate (Optional)**
- Sync the local database to Heroku, ensuring the changes are reflected:
   ```bash
   pgsync
   ```

This will truncate the Heroku database and replace it with the local data, ensuring both environments match.

---

### **5. Testing Front-End Code on Heroku**

When the developer wants to test only front-end code changes on Heroku:

#### **Step 1: Make Front-End Changes Locally**
- Update the front-end code (HTML, CSS, JS) and test locally.

#### **Step 2: Commit and Push to `development` Branch**
- Commit the front-end code changes to the `development` branch:
   ```bash
   git add .
   git commit -m "Update front-end code"
   git push origin development
   ```

#### **Step 3: Merge `development` into `stable-versions`**
- Merge `development` into `stable-versions`:
   ```bash
   git checkout stable-versions
   git merge development
   git push origin stable-versions
   ```

#### **Step 4: Test on Heroku**
- Heroku will deploy the changes automatically. You can now test the front-end code on Heroku.

---

### **Final Workflow Summary:**

1. **Model/Schema Changes**: Make changes locally, apply migrations, and push changes to Heroku.
2. **Flask App Code Updates**: Modify Flask code locally, commit, merge, and deploy to Heroku.
3. **New Dependencies**: Install locally, update `requirements.txt`, and Heroku will handle the installation on deployment.
4. **Database Content Changes**: Modify local database contents, then sync to Heroku with `truncate`.
5. **Front-End Testing**: Modify and test front-end code locally, then push to Heroku for deployment and testing.

-------
Here’s comprehensive workflow that includes both the **pgsync** tasks for syncing databases (remote to local and vice versa) and the **content table backup process** to iCloud. This workflow ensures you have a complete system for database synchronization and automated backups.

---

### **Comprehensive Workflow: Database Syncing and Automated Content Table Backups**

This guide walks you through syncing your databases between **local and Heroku** environments, as well as setting up an automated backup system for your **content tables** to iCloud using **Makefile**, **shell scripts**, and **cron jobs**.

---

### **Part 1: Setting Up Database Syncing with `pgsync`**

You’ll use `pgsync` to sync your local PostgreSQL database with the Heroku database in both directions: **local to Heroku** and **Heroku to local**. This process ensures your databases are always in sync for development and testing.

#### 1.1 What is a Makefile?

A **Makefile** is a configuration file used to automate tasks by defining rules that can be executed with the `make` command. This helps automate repetitive workflows such as database syncing or running scripts.

---

### **Step 1: Setting Up `pgsync` for Database Sync**

We’ll use the Makefile to define tasks for syncing your database **from local to Heroku** and **from Heroku to local**.

#### 1.1 Create the `.pgsync.yml` Configuration Files

You’ll need two configuration files for syncing databases in both directions:

1. **Create `.pgsync-local-to-remote.yml`:**

   This file defines the sync from your **local database to Heroku**.

   ```yaml
   from: postgres://admin:811976@localhost:5432/wscdb
   to: postgres://u97h703t4ikhdu:pd232fbc27d54c6216e5d6ac6e30f3649b650a2c1e3dddd16a07048f480188a97@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dd7v39guujdsvf

   exclude:
     - alembic_version

   truncate: true
   to_safe: true
   ```

2. **Create `.pgsync-remote-to-local.yml`:**

   This file defines the sync from **Heroku to your local database**.

   ```yaml
   from: postgres://u97h703t4ikhdu:pd232fbc27d54c6216e5d6ac6e30f3649b650a2c1e3dddd16a07048f480188a97@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dd7v39guujdsvf
   to: postgres://admin:811976@localhost:5432/wscdb

   exclude:
     - alembic_version

   truncate: true
   from_safe: true
   ```

---

### **Step 2: Define `pgsync` Commands in the Makefile**

We’ll use a Makefile to automate the process of running `pgsync` in both directions. This ensures that syncing databases is as simple as running a `make` command.

#### 2.1 Create the Makefile

1. In your project root directory, create a `Makefile`:
   ```bash
   touch Makefile
   ```

2. Open the file in a text editor:
   ```bash
   nano Makefile
   ```

3. Add the following content to the file:

```makefile
.PHONY: pgsync-local-to-remote pgsync-remote-to-local

# Sync from local to Heroku (truncate Heroku before syncing)
pgsync-local-to-remote:
    @pgsync --config .pgsync-local-to-remote.yml

# Sync from Heroku to local (truncate local before syncing)
pgsync-remote-to-local:
    @pgsync --config .pgsync-remote-to-local.yml
```

This will allow you to:
- **Sync local to Heroku** using `make pgsync-local-to-remote`.
- **Sync Heroku to local** using `make pgsync-remote-to-local`.

4. Save and close the Makefile.

#### 2.2 Run the Sync Commands

To test the sync commands, you can run:
- Sync **local to Heroku**:
   ```bash
   make pgsync-local-to-remote
   ```

- Sync **Heroku to local**:
   ```bash
   make pgsync-remote-to-local
   ```

---

### **Part 2: Setting Up Automated Content Table Backups to iCloud**

After ensuring your database is synced, it’s crucial to safeguard your **content tables** by creating regular backups stored in a third-party location (iCloud). This section will guide you through creating a shell script for backups, defining the command in your Makefile, and automating the process using cron jobs.

---

### **Step 3: Create a Shell Script for Content Table Backup**

This shell script will back up specific content-related tables from your PostgreSQL database and store the backup in **iCloud Drive**.

#### 3.1 Create the Shell Script

1. In your project directory, create the backup script:
   ```bash
   touch backup_to_icloud.sh
   ```

2. Open the file in a text editor:
   ```bash
   nano backup_to_icloud.sh
   ```

3. Add the following content:

```bash
#!/bin/bash

# Set variables
BACKUP_DIR=~/Library/Mobile\ Documents/com~apple~CloudDocs/ContentBackups
BACKUP_FILE="$BACKUP_DIR/content_backup_$(date +%Y%m%d%H%M%S).sql"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Perform the database backup
pg_dump -U admin -d wscdb -t contents -t references -t admin_report_templates -F c -f "$BACKUP_FILE"

# Confirm the backup was completed
if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_FILE"
else
    echo "Backup failed."
fi
```

4. Save and close the script, then make it executable:
   ```bash
   chmod +x backup_to_icloud.sh
   ```

---

### **Step 4: Add Backup Command to the Makefile**

We’ll add a rule in the Makefile to manually trigger content backups whenever needed.

#### 4.1 Update the Makefile

1. Open the Makefile:
   ```bash
   nano Makefile
   ```

2. Add the following rule for the backup:

```makefile
.PHONY: pgsync-local-to-remote pgsync-remote-to-local sync-to-icloud

# Sync from local to Heroku (truncate Heroku before syncing)
pgsync-local-to-remote:
    @pgsync --config .pgsync-local-to-remote.yml

# Sync from Heroku to local (truncate local before syncing)
pgsync-remote-to-local:
    @pgsync --config .pgsync-remote-to-local.yml

# Manual backup of content tables to iCloud
sync-to-icloud:
    @"/Users/zen/Library/Mobile\ Documents/com~apple~CloudDocs/ContentBackups/backup_to_icloud.sh"
```

3. Save and close the file.

#### 4.2 Run the Backup Command

To manually run a backup, simply use:

```bash
make sync-to-icloud
```

---

### **Step 5: Automate Backups with Cron Jobs**

A **cron job** is a scheduled task on Unix-like systems. We’ll set up a cron job to automate the backup at a regular interval.

#### 5.1 Open the Cron Editor

To edit your cron jobs, run:
```bash
crontab -e
```

#### 5.2 Add the Cron Job

Add the following line to schedule the backup every day at midnight:

```bash
0 0 * * * /Users/zen/Library/Mobile\ Documents/com~apple~CloudDocs/ContentBackups/backup_to_icloud.sh >> /Users/zen/logs/backup.log 2>&1
```

#### Explanation of the Cron Command:
- **`0 0 * * *`**: Runs the backup at midnight every day.
- **`>>`**: Appends output to the `backup.log` file for logging purposes.

#### 5.3 Save and Exit

After saving the cron job, you can verify it by running:
```bash
crontab -l
```

---

### **Final Workflow Summary:**

1. **pgsync Setup**:
   - Use `pgsync` to sync your database between **local** and **Heroku**.
   - Commands:
     - `make pgsync-local-to-remote` – Sync local to Heroku.
     - `make pgsync-remote-to-local` – Sync Heroku to local.

2. **Content Backup Setup**:
   - **Shell script**: Automates the backup of content tables to iCloud.
   - **Makefile command**: Allows you to manually trigger the backup with `make sync-to-icloud`.
   - **Cron job**: Automates the backup process daily at midnight.

This complete workflow ensures both your databases and content tables are synced and backed up regularly, giving you full control over data safety and availability. Let me know if you need further assistance!
