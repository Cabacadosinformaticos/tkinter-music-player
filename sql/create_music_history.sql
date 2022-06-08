-- Creates the table used by the SQL Server history of the music player.
-- The player also creates it by itself the first time it connects, so this
-- script is only needed if you want to prepare the database by hand.
CREATE TABLE music_history (
    Id               INT IDENTITY(1,1) PRIMARY KEY,
    Music_name       NVARCHAR(255) NOT NULL,
    Music_date       DATE          NOT NULL,  -- day the song was played
    Music_time       TIME(0)       NOT NULL,  -- time of day the song was played
    Duration_seconds INT           NULL       -- length of the song, used by the statistics
);

-- For a table created by an older version of the player:
-- ALTER TABLE music_history ADD Duration_seconds INT NULL;
