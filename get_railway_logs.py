#!/usr/bin/env python3
"""
Script to fetch Railway logs for debugging DSP sync issues.
You'll need to provide your Railway API token when prompted.

To get your Railway API token:
1. Go to https://railway.app/account/tokens
2. Create a new token
3. Copy and paste it when prompted
"""

import requests
import json
from datetime import datetime

def get_railway_logs(api_token):
    """Fetch logs from Railway API using GraphQL"""

    # Railway GraphQL endpoint
    url = "https://backboard.railway.app/graphql/v2"

    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    # First, get the list of projects
    projects_query = """
    query {
        me {
            projects {
                edges {
                    node {
                        id
                        name
                        services {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    print("🔍 Fetching Railway projects...")
    response = requests.post(url, json={"query": projects_query}, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to fetch projects: {response.status_code}")
        print(response.text)
        return

    data = response.json()

    if "errors" in data:
        print(f"❌ GraphQL Error: {data['errors']}")
        return

    projects = data.get("data", {}).get("me", {}).get("projects", {}).get("edges", [])

    if not projects:
        print("❌ No projects found")
        return

    # Find the amazon-dsp project
    target_project = None
    for project in projects:
        node = project["node"]
        if "amazon" in node["name"].lower() or "dsp" in node["name"].lower():
            target_project = node
            break

    if not target_project:
        # Use first project if no match
        target_project = projects[0]["node"]

    print(f"✅ Found project: {target_project['name']}")

    # Get services
    services = target_project.get("services", {}).get("edges", [])

    if not services:
        print("❌ No services found in project")
        return

    # Get deployments and logs for each service
    for service in services:
        service_node = service["node"]
        service_id = service_node["id"]
        service_name = service_node["name"]

        print(f"\n📦 Service: {service_name}")
        print("=" * 50)

        # Get deployments
        deployments_query = f"""
        query {{
            deployments(
                first: 5
                input: {{
                    serviceId: "{service_id}"
                }}
            ) {{
                edges {{
                    node {{
                        id
                        status
                        createdAt
                        meta {{
                            startedAt
                            endedAt
                        }}
                    }}
                }}
            }}
        }}
        """

        response = requests.post(url, json={"query": deployments_query}, headers=headers)

        if response.status_code != 200:
            print(f"❌ Failed to fetch deployments: {response.status_code}")
            continue

        deployment_data = response.json()
        deployments = deployment_data.get("data", {}).get("deployments", {}).get("edges", [])

        if deployments:
            latest_deployment = deployments[0]["node"]
            deployment_id = latest_deployment["id"]

            print(f"Latest deployment: {latest_deployment['status']}")
            print(f"Created: {latest_deployment['createdAt']}")

            # Get logs for the deployment
            logs_query = f"""
            query {{
                deploymentLogs(
                    deploymentId: "{deployment_id}"
                    limit: 100
                    filter: {{}}
                ) {{
                    message
                    timestamp
                    severity
                }}
            }}
            """

            response = requests.post(url, json={"query": logs_query}, headers=headers)

            if response.status_code == 200:
                logs_data = response.json()
                logs = logs_data.get("data", {}).get("deploymentLogs", [])

                print(f"\n📜 Recent logs (last {len(logs)} entries):")
                print("-" * 50)

                # Filter for DSP-related logs
                dsp_keywords = ["dsp", "DSP", "advertiser", "seats", "sync", "account", "unauthorized", "403", "token", "refresh"]

                relevant_logs = []
                for log in logs:
                    message = log.get("message", "").lower()
                    if any(keyword.lower() in message for keyword in dsp_keywords):
                        relevant_logs.append(log)

                if relevant_logs:
                    print("\n🎯 DSP-related logs found:")
                    for log in relevant_logs[-20:]:  # Show last 20 relevant logs
                        timestamp = log.get("timestamp", "")
                        severity = log.get("severity", "INFO")
                        message = log.get("message", "")

                        # Format timestamp if present
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                pass

                        # Color code by severity
                        severity_icon = {
                            "ERROR": "❌",
                            "WARNING": "⚠️",
                            "INFO": "ℹ️",
                            "DEBUG": "🔍"
                        }.get(severity.upper(), "•")

                        print(f"{severity_icon} [{timestamp}] {message[:200]}")
                else:
                    print("No DSP-related logs found. Showing recent general logs:")
                    for log in logs[-10:]:  # Show last 10 general logs
                        timestamp = log.get("timestamp", "")
                        message = log.get("message", "")

                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                timestamp = dt.strftime("%H:%M:%S")
                            except:
                                pass

                        print(f"[{timestamp}] {message[:150]}")

def main():
    print("🚂 Railway Logs Fetcher")
    print("=" * 50)
    print("\nTo get your Railway API token:")
    print("1. Go to https://railway.app/account/tokens")
    print("2. Create a new token")
    print("3. Copy and paste it below\n")

    api_token = input("Enter your Railway API token: ").strip()

    if not api_token:
        print("❌ No token provided")
        return

    get_railway_logs(api_token)

if __name__ == "__main__":
    main()