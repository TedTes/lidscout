alter table if exists opportunities
    alter column cluster_id drop not null;

alter table if exists opportunities
    drop constraint if exists opportunities_cluster_id_fkey;

alter table if exists opportunities
    drop constraint if exists opportunities_cluster_or_theme_check;

alter table if exists opportunities
    add constraint opportunities_cluster_or_theme_check
        check (cluster_id is not null or source_theme_id is not null);
