-- Switch all HackerNews Algolia sources from tags=story to tags=comment.
-- Story titles are mostly news/launches; comments carry the actual complaints.
update niche_sources
set locator = replace(locator, 'tags=story', 'tags=comment')
where locator like '%hn.algolia.com%tags=story%';
