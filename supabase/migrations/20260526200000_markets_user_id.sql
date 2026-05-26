alter table markets
    add column if not exists user_id uuid references users(id) on delete cascade;

create index if not exists markets_user_id_idx
    on markets (user_id)
    where user_id is not null;
