#!/bin/bash
# Send a test email to a local user
# Usage: ./send_test_email.sh <username> <subject> <body>

USER=${1:-testmail}
SUBJECT=${2:-"Test Email"}
BODY=${3:-"This is a test email from the mail agent test server."}

echo "$BODY" | mail -s "$SUBJECT" "$USER@localhost"

echo "Sent test email to $USER@localhost"
echo "Subject: $SUBJECT"
