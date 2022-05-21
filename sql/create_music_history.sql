-- Creates the table used by the database version of the music player (SQL Server).
-- Run it once on your own database before starting src/db_player.py.
CREATE TABLE music_history (
    Id         INT IDENTITY(1,1) PRIMARY KEY,
    Music_name NVARCHAR(255) NOT NULL,
    Music_date DATE          NOT NULL,  -- day the song was played
    Music_time TIME(0)       NOT NULL   -- time of day the song was played
);
