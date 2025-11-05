# Email Open Tracker

This is a Flask application that tracks email opens using a 1x1 pixel. 

## Features

- Logs email opens (IP, User-Agent, recipient, subject, sender)
- Sends email alerts to sender when emails are opened
- Prevents duplicate opens within 5 minutes
- Provides a simple /logs dashboard
- Automatically generates a transparent pixel if missing
