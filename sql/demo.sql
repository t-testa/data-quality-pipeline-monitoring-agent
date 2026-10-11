-- Optional SQL Server fixture. Run ONLY in a separately provisioned DQDemo database.
-- Does not create a database or touch NorthstarBI. SQLite loader is the automated demo path.
IF DB_NAME() <> N'DQDemo'
    THROW 51000, 'This fixture may run only in the isolated DQDemo database.', 1;
SET XACT_ABORT ON;
BEGIN TRANSACTION;
IF OBJECT_ID(N'dbo.customers', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.customers (id int NOT NULL, name varchar(80) NULL, updated_at datetime2 NOT NULL);
    CREATE TABLE dbo.orders (id int PRIMARY KEY, customer_id int NOT NULL,
        amount decimal(12,2) NOT NULL, cost decimal(12,2) NOT NULL,
        updated_at datetime2 NOT NULL, version int NOT NULL, deleted int NOT NULL DEFAULT 0);
    CREATE TABLE dbo.warehouse (id int PRIMARY KEY, amount decimal(12,2) NOT NULL);
    DECLARE @i int = 1;
    WHILE @i <= 10
    BEGIN
        INSERT dbo.customers VALUES(@i, CONCAT('Synthetic customer ', @i), SYSUTCDATETIME());
        SET @i += 1;
    END;
    SET @i = 1;
    WHILE @i <= 100
    BEGIN
        INSERT dbo.orders VALUES(@i, ((@i-1)%10)+1, 100, 60, SYSUTCDATETIME(), @i, 0);
        INSERT dbo.warehouse VALUES(@i, 100);
        SET @i += 1;
    END;
END;
COMMIT TRANSACTION;
-- To test quality against this optional fixture, point a reviewed rule catalog at these tables
-- using a separate SELECT-only identity. This script has not been executed against NorthstarBI.
