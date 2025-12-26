#!/bin/bash

# MongoDB initialization script with credential validation
# Fails and prevents container startup if credentials are not configured

set -e  # Exit on any error

# Validate required environment variables
if [ -z "$MONGO_USER" ]; then
  echo "ERROR: MONGO_USER environment variable is not set"
  exit 1
fi

if [ -z "$MONGO_PASSWORD" ]; then
  echo "ERROR: MONGO_PASSWORD environment variable is not set"
  exit 1
fi

if [ -z "$MONGO_DB_NAME" ]; then
  echo "ERROR: MONGO_DB_NAME environment variable is not set"
  exit 1
fi

echo "Initializing MongoDB with user: $MONGO_USER"
echo "Database: $MONGO_DB_NAME"

# Wait for MongoDB to be ready
until mongosh --eval "db.adminCommand('ping')" &> /dev/null; do
  echo "Waiting for MongoDB to be ready..."
  sleep 2
done

echo "MongoDB is ready. Setting up user and database..."

# Create user and database using mongosh
# Must execute in the application database scope for proper authentication
if ! mongosh << MONGO_SCRIPT
  // Connect to the application database
  db = db.getSiblingDB('$MONGO_DB_NAME');
  
  // Create the application user in the correct database scope
  try {
    db.createUser({
      user: '$MONGO_USER',
      pwd: '$MONGO_PASSWORD',
      roles: [
        {
          role: 'dbOwner',
          db: '$MONGO_DB_NAME'
        }
      ]
    });
    print('User $MONGO_USER created successfully in database $MONGO_DB_NAME');
  } catch (e) {
    if (e.code === 51003) {
      print('User $MONGO_USER already exists in database $MONGO_DB_NAME');
    } else {
      print('ERROR: Failed to create user: ' + e.message);
      throw e;
    }
  }
  
  // Verify the database exists
  print('Database $MONGO_DB_NAME is initialized');
  print('MongoDB initialization completed successfully');
MONGO_SCRIPT
then
  echo "ERROR: MongoDB initialization failed - user creation or verification error"
  exit 1
fi

echo "MongoDB initialization completed successfully"
exit 0
