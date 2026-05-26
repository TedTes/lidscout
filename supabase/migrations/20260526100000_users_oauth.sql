alter table users
    alter column password_hash drop not null;

alter table users
    add column if not exists google_id text unique;

create index if not exists users_google_id_idx
    on users (google_id)
    where google_id is not null;
