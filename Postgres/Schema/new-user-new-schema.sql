DO $$ 
DECLARE 
    v_schema_name TEXT := 'your_schema';  -- Replace with container-specific schema name
    v_user_name TEXT := 'your_user';      -- Replace with container-specific username
    v_user_password TEXT := 'your_password';  -- Set a secure password for each user
    schema_exists BOOLEAN;
    user_exists BOOLEAN;
BEGIN
    -- Check if schema exists
    SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = v_schema_name) 
    INTO schema_exists;
    
    -- Create schema if it does not exist
    IF NOT schema_exists THEN
        EXECUTE format('CREATE SCHEMA %I', v_schema_name);
    END IF;

    -- Check if user exists
    SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_user_name) 
    INTO user_exists;
    
    -- Create user if it does not exist
    IF NOT user_exists THEN
        EXECUTE format('CREATE USER %I WITH PASSWORD %L', v_user_name, v_user_password);
    END IF;

    -- Grant ownership of schema to the user
    EXECUTE format('ALTER SCHEMA %I OWNER TO %I', v_schema_name, v_user_name);

    -- Set the default schema for the user
    EXECUTE format('ALTER ROLE %I SET search_path TO %I, public', v_user_name, v_schema_name);

    -- Grant privileges on the schema to the user
    EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', v_schema_name, v_user_name);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', v_schema_name, v_user_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I 
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', v_schema_name, v_user_name);
    EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA %I TO %I', v_schema_name, v_user_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I 
                    GRANT ALL PRIVILEGES ON SEQUENCES TO %I', v_schema_name, v_user_name);
END $$;
