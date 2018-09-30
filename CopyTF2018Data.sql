insert
into	core_festival
		(id, uuid, created, updated, name, title, is_active)
values	(1, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 'TF2018', 'Fringe Theatrefest 2018', false);

insert
into	core_festival
		(id, uuid, created, updated, name, title, is_active)
values	(2, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 'TF2019', 'Fringe Theatrefest 2019', false);

delete from django_site;
insert
into	django_site
		(id, domain, name)
values	(1, 'localhost', 'development');

insert
into	core_siteinfo
		(id, uuid, created, updated, site_id, festival_id)
values	(1, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 1, 1)

insert
into public.program_company
	(id, uuid, created, updated, festival_id, name, image, listing, listing_short, detail, address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram)
select
	id, uuid, created, updated, 1, name, image, description, '', '', address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram
from tf2018.program_company;

insert
into public.program_companycontact
	(company_id, uuid, created, updated, name, role, telno, mobile, email)
select
	id, uuid_generate_v4(), created, updated, primary_contact, 'Primary', primary_telno, primary_mobile, primary_email
from tf2018.program_company
where primary_contact <> '';

insert
into public.program_companycontact
	(company_id, uuid, created, updated, name, role, telno, mobile, email)
select
	id, uuid_generate_v4(), created, updated, secondary_contact, 'Secondary', secondary_telno, secondary_mobile, secondary_email
from tf2018.program_company
where secondary_contact <> '';

insert
into public.program_venue
	(id, uuid, created, updated, festival_id, name, image, listing, listing_short, detail, address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram, is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
select
	id, uuid, created, updated, 1, name, image, description, '', '', address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram, is_ticketed, is_scheduled, is_searchable, capacity, map_index, color
from tf2018.program_venue;

insert
into public.program_venuecontact
	(venue_id, uuid, created, updated, name, role, telno, mobile, email)
select
	id, uuid_generate_v4(), created, updated, primary_contact, 'Primary', primary_telno, primary_mobile, primary_email
from tf2018.program_venue
where primary_contact <> '';

insert
into public.program_venuecontact
	(venue_id, uuid, created, updated, name, role, telno, mobile, email)
select
	id, uuid_generate_v4(), created, updated, secondary_contact, 'Secondary', secondary_telno, secondary_mobile, secondary_email
from tf2018.program_venue
where secondary_contact <> '';

insert
into public.program_venuesponsor
	(venue_id, uuid, created, updated, name, image, color, background, message, website, facebook, twitter, instagram)
select
	id, uuid_generate_v4(), created, updated, sponsor_name, sponsor_image, sponsor_color, sponsor_background, sponsor_message, '', '', '', ''
from tf2018.program_venue
where sponsor_name <> '';

insert
into public.program_genre
	(id, uuid, created, updated, festival_id, name)
select
	id, uuid, created, updated, 1, name
from tf2018.program_genre;

insert
into public.program_show
	(id, uuid, created, updated, festival_id, name, company_id, venue_id, image, listing, listing_short, detail, website, facebook, twitter, instagram, genre_text, has_warnings, age_range, duration, is_suspended, is_cancelled, replaced_by_id)
select
	id, uuid, created, updated, 1, name, company_id, venue_id, image, long_description, description, html_description, website, facebook, twitter, instagram, genre_display, has_warnings, age_range, duration, is_suspended, is_cancelled, replaced_by_id
from tf2018.program_show;

insert
into public.program_show_genres
	(id, show_id, genre_id)
select
	id, show_id, genre_id
from tf2018.program_show_genres;

insert
into public.program_showperformance
	(id, uuid, created, updated, show_id, date, time)
select
	id, uuid, created, updated, show_id, date, time
from tf2018.program_performance;

insert
into public.program_showreview
	(id, uuid, created, updated, show_id, source, rating, body, url)
select
	id, uuid, created, updated, show_id, source, rating, body, url
from tf2018.program_review;

insert
into public.program_showimage
	(id, uuid, created, updated, show_id, name, image)
select
	id, uuid, created, updated, show_id, name, image
from tf2018.program_showimage;


select setval('django_site_id_seq', (select coalesce(max(id), 1) from django_site));
select setval('core_festival_id_seq', (select coalesce(max(id), 1) from core_festival));
select setval('core_siteinfo_id_seq', (select coalesce(max(id), 1) from core_siteinfo));
select setval('core_user_id_seq', (select coalesce(max(id), 1) from core_user));
select setval('program_company_id_seq', (select coalesce(max(id), 1) from program_company));
select setval('program_companycontact_id_seq', (select coalesce(max(id), 1) from program_companycontact));
select setval('program_genre_id_seq', (select coalesce(max(id), 1) from program_genre));
select setval('program_show_genres_id_seq', (select coalesce(max(id), 1) from program_show_genres));
select setval('program_show_id_seq', (select coalesce(max(id), 1) from program_show));
select setval('program_showimage_id_seq', (select coalesce(max(id), 1) from program_showimage));
select setval('program_showperformance_id_seq', (select coalesce(max(id), 1) from program_showperformance));
select setval('program_showreview_id_seq', (select coalesce(max(id), 1) from program_showreview));
select setval('program_venue_id_seq', (select coalesce(max(id), 1) from program_venue));
select setval('program_venuesponsor_id_seq', (select coalesce(max(id), 1) from program_venuesponsor));
select setval('program_venuecontact_id_seq', (select coalesce(max(id), 1) from program_venuecontact));

