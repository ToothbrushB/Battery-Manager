CREATE TABLE IF NOT EXISTS 'battery' (
  'id' INTEGER PRIMARY KEY AUTOINCREMENT,
  'status' TEXT NOT NULL,
  'cycles' INTEGER NOT NULL,
  'date_purchased' DATE NOT NULL,
  'goodness' TEXT NOT NULL,
  'drainage_curve' TEXT NOT NULL,
  'location_id' INTEGER NOT NULL,
  FOREIGN KEY('location_id') REFERENCES 'location'('id')
);

CREATE TABLE IF NOT EXISTS 'history' (
  'id' INTEGER PRIMARY KEY AUTOINCREMENT,
  'battery_id' INTEGER NOT NULL,
  'date' DATE NOT NULL,
  'status' TEXT NOT NULL,
  'location_id' INTEGER NOT NULL,
  'match_id' INTEGER,
  FOREIGN KEY('battery_id') REFERENCES 'battery'('id'),
  FOREIGN KEY('location_id') REFERENCES 'location'('id')
);

CREATE TABLE IF NOT EXISTS 'location' (
  'id' INTEGER PRIMARY KEY AUTOINCREMENT,
  'name' TEXT NOT NULL,
  'parent_id' INTEGER,
  FOREIGN KEY('parent_id') REFERENCES 'location'('id')
);

CREATE TABLE IF NOT EXISTS 'sync' (
  'id' INTEGER PRIMARY KEY AUTOINCREMENT,
  'date' DATE NOT NULL,
  'status' TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS 'matches' (
 'id' INTEGER PRIMARY KEY AUTOINCREMENT,
 'time' DATE NOT NULL,
 'status' TEXT NOT NULL,
 'event_id' TEXT NOT NULL,
 'red1_id' INTEGER NOT NULL,
 'red2_id' INTEGER NOT NULL,
 'red3_id' INTEGER NOT NULL,
  'blue1_id' INTEGER NOT NULL,
  'blue2_id' INTEGER NOT NULL,
  'blue3_id' INTEGER NOT NULL,
  'match_number' INTEGER NOT NULL,
  FOREIGN KEY('red1_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('red2_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('red3_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('blue1_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('blue2_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('blue3_id') REFERENCES 'teams'('id'),
  FOREIGN KEY('event_id') REFERENCES 'events'('id')
 
);

CREATE TABLE IF NOT EXISTS 'events' (
 'id' TEXT PRIMARY KEY,
 'name' TEXT NOT NULL,
 'date' DATE NOT NULL,
 'event_key' TEXT NOT NULL,
);

CREATE TABLE IF NOT EXISTS 'teams' (
 'id' INTEGER PRIMARY KEY AUTOINCREMENT,
 'number' INTEGER NOT NULL,
 'name' TEXT NOT NULL,
 'location_id' INTEGER NOT NULL,
 FOREIGN KEY('location_id') REFERENCES 'location'('id')
);