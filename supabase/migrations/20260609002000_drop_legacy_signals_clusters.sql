-- Drop legacy signals and clusters tables now that the pipeline fully uses
-- the accumulated findings/themes model.
-- These tables were created in the initial schema (20260520152000_init_lidscout_schema.sql)
-- and are no longer written to or read from the application.

drop table if exists clusters cascade;
drop table if exists signals  cascade;
drop table if exists posts     cascade;
