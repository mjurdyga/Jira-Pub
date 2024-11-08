import requests
import json
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MantisJiraSync:
    def __init__(self, 
                 mantis_url: str,
                 mantis_token: str,
                 jira_url: str,
                 jira_email: str,
                 jira_token: str,
                 categories_to_sync: List[str],
                 db_path: str = 'sync_status.db'):
        self.mantis_url = mantis_url
        self.mantis_headers = {
            'Authorization': mantis_token,
            'Content-Type': 'application/json'
        }
        self.jira_url = jira_url
        self.jira_auth = (jira_email, jira_token)
        self.categories_to_sync = categories_to_sync
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database to track synced tickets"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS synced_tickets (
                    mantis_id INTEGER PRIMARY KEY,
                    jira_key TEXT,
                    sync_time TIMESTAMP,
                    category TEXT
                )
            ''')

    def get_mantis_issues(self, project_id: str, page_size: int = 50, page: int = 1) -> List[Dict]:
        """Fetch issues from MantisBT API with pagination"""
        endpoint = f"{self.mantis_url}/api/rest/issues"
        params = {
            'project_id': project_id,
            'page_size': page_size,
            'page': page
        }
        response = requests.get(endpoint, headers=self.mantis_headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Mantis issues: {response.text}")
        return response.json()['issues']

    def create_jira_issue(self, mantis_data: Dict) -> Dict:
        """Create a new Jira issue from Mantis data"""
        endpoint = f"{self.jira_url}/rest/api/3/issue"
        
        jira_payload = {
            "fields": {
                "project": {"key": "Demo Scrum"},
                "summary": f"[Mantis #{mantis_data['id']}] {mantis_data['summary']}",
                "description": {
                    "type": "task",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{
                                "text": mantis_data['description'],
                                "type": "text"
                            }]
                        },
                        {
                            "type": "paragraph",
                            "content": [{
                                "text": f"\nLinked Mantis ticket: {self.mantis_url}/view.php?id={mantis_data['id']}",
                                "type": "text"
                            }]
                        }
                    ]
                },
                "issuetype": {"name": self.map_issue_type(mantis_data['category']['name'])},
                "priority": self.map_priority(mantis_data['priority'])
            }
        }
        
        response = requests.post(
            endpoint,
            json=jira_payload,
            auth=self.jira_auth
        )
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to create Jira issue: {response.text}")
        return response.json()

    def update_mantis_with_jira_link(self, mantis_id: int, jira_key: str) -> None:
        """Add Jira reference to Mantis ticket notes"""
        endpoint = f"{self.mantis_url}/api/rest/issues/{mantis_id}/notes"
        note_data = {
            "text": f"Linked Jira ticket: {self.jira_url}/browse/{jira_key}"
        }
        
        response = requests.post(
            endpoint,
            headers=self.mantis_headers,
            json=note_data
        )
        if response.status_code != 201:
            raise Exception(f"Failed to update Mantis ticket: {response.text}")

    def is_ticket_synced(self, mantis_id: int) -> bool:
        """Check if a Mantis ticket has already been synced"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT jira_key FROM synced_tickets WHERE mantis_id = ?",
                (mantis_id,)
            )
            return cursor.fetchone() is not None

    def mark_ticket_synced(self, mantis_id: int, jira_key: str, category: str):
        """Mark a ticket as synced in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO synced_tickets (mantis_id, jira_key, sync_time, category)
                VALUES (?, ?, ?, ?)
                """,
                (mantis_id, jira_key, datetime.now(), category)
            )

    @staticmethod
    def map_issue_type(category: str) -> str:
        """Map MantisBT category to Jira issue type"""
        type_map = {
            'bug': 'Bug',
            'feature': 'Story',
            'enhancement': 'Improvement',
            'task': 'Task'
        }
        return type_map.get(category.lower(), 'Task')

    @staticmethod
    def map_priority(mantis_priority: Dict) -> Dict:
        """Map MantisBT priority to Jira priority"""
        priority_map = {
            'normal': {'name': 'Medium'},
            'high': {'name': 'High'},
            'urgent': {'name': 'Highest'},
            'low': {'name': 'Low'},
            'none': {'name': 'Lowest'}
        }
        return priority_map.get(mantis_priority['name'].lower(), {'name': 'Medium'})

    def sync_new_tickets(self, project_id: str):
        """Sync new tickets from Mantis to Jira"""
        try:
            page = 1
            while True:
                issues = self.get_mantis_issues(project_id, page=page)
                if not issues:
                    break

                for issue in issues:
                    try:
                        # Check if ticket should be synced
                        if (issue['category']['name'] not in self.categories_to_sync or 
                            self.is_ticket_synced(issue['id'])):
                            continue

                        # Create Jira issue
                        jira_response = self.create_jira_issue(issue)
                        jira_key = jira_response['key']

                        # Update Mantis with Jira link
                        self.update_mantis_with_jira_link(issue['id'], jira_key)

                        # Mark as synced
                        self.mark_ticket_synced(
                            issue['id'],
                            jira_key,
                            issue['category']['name']
                        )

                        logger.info(f"Synced Mantis #{issue['id']} to Jira {jira_key}")

                    except Exception as e:
                        logger.error(f"Error syncing ticket {issue['id']}: {str(e)}")

                page += 1
                time.sleep(1)  # Rate limiting

        except Exception as e:
            logger.error(f"Error in sync process: {str(e)}")

def main():
    # Initialize the syncer
    syncer = MantisJiraSync(
        mantis_url="https://mantis.xxxxxxxx/",
        mantis_token="xxxxxx",
        jira_url="https://xxxxxx.atlassian.net/",
        jira_email="xxxxx@gmail.com",
        jira_token="xxxxxx",
        categories_to_sync=["Bug", "Feature Request"]  # Add your categories here
    )

    while True:
        try:
            syncer.sync_new_tickets("2")
            logger.info("Sync cycle completed")
            time.sleep(100)  # Wait 2 minutes between sync cycles
        except Exception as e:
            logger.error(f"Error in sync cycle: {str(e)}")
            time.sleep(60)  # Wait 1 minute on error before retrying

if __name__ == "__main__":
    main()
