alter table competitors
    drop constraint if exists competitors_market_id_fkey;

alter table competitors
    add constraint competitors_market_id_fkey
    foreign key (market_id)
    references markets(id)
    on delete cascade;
