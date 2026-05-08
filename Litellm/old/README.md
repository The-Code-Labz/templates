# Get the code
git clone https://github.com/BerriAI/litellm

# Go to folder
cd litellm

# edit the compose file to your liking - you can change the ports, the volumes, networks, the environment variables, etc
# you can also add more services to the compose file if you want to add more features to the application

# The container will not take the .env file as it is, so we need to go insid the container to make the changes

# Add the master key - you can change this after setup
docker exec container_name echo 'LITELLM_MASTER_KEY="sk-1234"' > .env

# Add the litellm salt key - you cannot change this after adding a model
# It is used to encrypt / decrypt your LLM API Key credentials
# We recommned - https://1password.com/password-generator/ 
# password generator to get a random hash for litellm salt key
docker exec container_name echo 'LITELLM_SALT_KEY="sk-1234"' >> .env

# now the default username and password is admin / your master key if there are issues and when you try to login you get the error user not found
# or invalid password, you can change the username and password by manually adding the user to the database inside the db container
docker exec -it your_container_name psql -U your_username -d your_database

# or go into the docker folder and change the .env.example file to .env and add # the variables there

# then run the following command to add a user
INSERT INTO "LiteLLM_UserTable" (user_id, user_alias, user_role, user_email, created_at, updated_at)
VALUES ('default_user_id', 'Admin', 'admin', 'admin@example.com', NOW(), NOW());

# to generate a hashed password you can use the following pyhton code
import bcrypt

password = "your_secure_password".encode('utf-8')  # Replace with your actual password
hashed = bcrypt.hashpw(password, bcrypt.gensalt())

print(hashed.decode('utf-8'))  # Copy this for the database
# or you can use the python docker container template check the template folder for more information

# then run the following command to add a password
UPDATE "LiteLLM_UserTable" 
SET password = '$2b$12$examplehashedpasswordhere' 
WHERE user_id = 'default_user_id';
