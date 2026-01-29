# Quick Reference - Device Update System

## 🚀 Common Operations

### 1. Production Update (Full Workflow)
```bash
./update_production.sh devices.json
```
✅ Validates → Dry runs → Asks confirmation → Updates → Shows stats

---

### 2. Validate JSON Only
```bash
docker exec eos_tracker_api python database/device_cli.py validate /tmp/devices.json
```

---

### 3. Manual Update (Step by Step)
```bash
# Copy file to container
docker cp devices.json eos_tracker_api:/tmp/devices.json

# Validate
docker exec eos_tracker_api python database/device_cli.py validate /tmp/devices.json

# Dry run
docker exec eos_tracker_api python database/device_cli.py update /tmp/devices.json --dry-run

# Apply
docker exec eos_tracker_api python database/device_cli.py update /tmp/devices.json

# Cleanup
docker exec eos_tracker_api rm /tmp/devices.json
```

---

### 4. Backup Database
```bash
# Export to container
docker exec eos_tracker_api python database/device_cli.py export /tmp/backup.json

# Copy to host
docker cp eos_tracker_api:/tmp/backup.json ./backup_$(date +%Y%m%d).json

# Cleanup
docker exec eos_tracker_api rm /tmp/backup.json
```

---

### 5. View Statistics
```bash
docker exec eos_tracker_api python database/device_cli.py stats
```

---

## 📝 JSON Template

```json
{
  "version": "1.0",
  "updated_at": "2026-01-29T10:30:00Z",
  "devices": [
    {
      "vendor": "Cisco",
      "model": "Catalyst 9300",
      "device_type": "Switch",
      "eos_date": "2027-12-31",
      "eol_date": "2028-12-31",
      "description": "Next-gen campus switch"
    }
  ]
}
```

---

## ⚠️ Critical Reminders

1. **Always dry run first** - `--dry-run` flag
2. **Backup before major updates** - Use export command
3. **Validate JSON** - Before copying to production
4. **Check container name** - `docker ps`
5. **Monitor logs** - `docker logs -f eos_tracker_api`

---

## 🔧 Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Container not found | `docker ps` to find correct name |
| Permission denied | `chmod +x update_production.sh` |
| Invalid JSON | Check format with `cat file.json \| jq .` |
| Connection failed | Check DATABASE_URL and DB container |

---

## 📊 Understanding Output

### Dry Run Output
```
[DRY RUN] Would insert: Cisco Catalyst 9200  ← New device
[DRY RUN] Would update: Cisco ISR 4461       ← Changed data
Skipped (no changes): Juniper EX4300         ← Already current
```

### Statistics
```
Inserted:  5   ← New devices added
Updated:   3   ← Existing devices modified
Skipped:   2   ← No changes needed
Failed:    0   ← Errors encountered
Total:     10  ← Total devices processed
```

---

## 🎯 Best Practices

✅ Test in development first  
✅ Use descriptive filenames: `devices_jan2026_v1.json`  
✅ Version your JSON files  
✅ Keep backups of old JSONs  
✅ Archive processed files  
✅ Monitor application logs after updates  

---

## 📞 Emergency Rollback

If something goes wrong:

```bash
# 1. Stop accepting traffic (optional)
docker pause eos_tracker_api

# 2. Restore from backup
docker cp backup_20260129.json eos_tracker_api:/tmp/restore.json
docker exec eos_tracker_api python database/device_cli.py update /tmp/restore.json

# 3. Verify
docker exec eos_tracker_api python database/device_cli.py stats

# 4. Resume traffic
docker unpause eos_tracker_api
```

---

**Tip:** Bookmark this file for quick access! 🔖
