.PHONY: pgsync-local-to-remote pgsync-remote-to-local
# Sync from local to Heroku (truncate Heroku before syncing)
pgsync-local-to-remote:
	@pgsync --config .pgsync-local-to-remote.yml
# Sync from Heroku to local (truncate local before syncing)
pgsync-remote-to-local:
	@pgsync --config .pgsync-remote-to-local.yml
# Manual backup of content tables to iCloud
sync-to-icloud:
	@/Users/zen/Library/Mobile\ Documents/com~apple~CloudDocs/ContentBackups/backup_to_icloud.sh
