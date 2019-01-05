/**********/
/* Django */
/**********/
delete from django_site;

insert
into	django_site
		(id, domain, name)
values	(1, 'localhost', 'development');

select setval('django_site_id_seq', (select coalesce(max(id), 1) from django_site));

/********/
/* Core */
/********/
-- festival
insert
into	core_festival
		(id, uuid, created, updated, name, title, is_active)
values	(1, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 'TF2018', 'Fringe Theatrefest 2018', false);

insert
into	core_festival
		(id, uuid, created, updated, name, title, is_active)
values	(2, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 'TF2019', 'Fringe Theatrefest 2019', false);

select setval('core_festival_id_seq', (select coalesce(max(id), 1) from core_festival));

-- siteinfo
insert
into	core_siteinfo
		(id, uuid, created, updated, site_id, festival_id)
values	(1, uuid_generate_v4(), clock_timestamp(), clock_timestamp(), 1, 1)

select setval('core_siteinfo_id_seq', (select coalesce(max(id), 1) from core_siteinfo));

-- user
insert
into	core_user
		(id, uuid, created, updated, festival_id, site_id, email, password, last_login, is_superuser, first_name, last_name, is_active, is_admin, is_box_office, is_manager, is_volunteer)
select
		id, uuid, date_joined, date_joined, 1, 1, email, '', last_login, is_superuser, first_name, last_name, is_active, is_admin, false, false, is_volunteer
from	tf2018.accounts_user;

select setval('core_user_id_seq', (select coalesce(max(id), 1) from core_user));

/***********/
/* Program */
/***********/
--company
insert
into public.program_company
	(id, uuid, created, updated, festival_id, name, image, listing, listing_short, detail, address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram)
select
	id, uuid, created, updated, 1, name, image, description, '', '', address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram
from tf2018.program_company;

select setval('program_company_id_seq', (select coalesce(max(id), 1) from program_company));

-- companycontact
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

select setval('program_companycontact_id_seq', (select coalesce(max(id), 1) from program_companycontact));

-- venue
insert
into public.program_venue
	(id, uuid, created, updated, festival_id, name, image, listing, listing_short, detail, address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram, is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
select
	id, uuid, created, updated, 1, name, image, description, '', '', address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram, is_ticketed, is_scheduled, is_searchable, capacity, map_index, color
from tf2018.program_venue;

select setval('program_venue_id_seq', (select coalesce(max(id), 1) from program_venue));

-- venuecontact
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

select setval('program_venuecontact_id_seq', (select coalesce(max(id), 1) from program_venuecontact));

-- venuesponsor
insert
into public.program_venuesponsor
	(venue_id, uuid, created, updated, name, image, color, background, message, website, facebook, twitter, instagram)
select
	id, uuid_generate_v4(), created, updated, sponsor_name, sponsor_image, sponsor_color, sponsor_background, sponsor_message, '', '', '', ''
from tf2018.program_venue
where sponsor_name <> '';

select setval('program_venuesponsor_id_seq', (select coalesce(max(id), 1) from program_venuesponsor));

-- genre
insert
into public.program_genre
	(id, uuid, created, updated, festival_id, name)
select
	id, uuid, created, updated, 1, name
from tf2018.program_genre;

select setval('program_genre_id_seq', (select coalesce(max(id), 1) from program_genre));

-- show
insert
into public.program_show
	(id, uuid, created, updated, festival_id, name, company_id, venue_id, image, listing, listing_short, detail, website, facebook, twitter, instagram, genre_text, has_warnings, age_range, duration, is_suspended, is_cancelled, replaced_by_id)
select
	id, uuid, created, updated, 1, name, company_id, venue_id, image, long_description, description, html_description, website, facebook, twitter, instagram, genre_display, has_warnings, age_range, duration, is_suspended, is_cancelled, replaced_by_id
from tf2018.program_show;

select setval('program_show_id_seq', (select coalesce(max(id), 1) from program_show));

-- show_genres
insert
into public.program_show_genres
	(id, show_id, genre_id)
select
	id, show_id, genre_id
from tf2018.program_show_genres;

select setval('program_show_genres_id_seq', (select coalesce(max(id), 1) from program_show_genres));

-- showperformance
insert
into public.program_showperformance
	(id, uuid, created, updated, show_id, date, time)
select
	id, uuid, created, updated, show_id, date, time
from tf2018.program_performance;

select setval('program_showperformance_id_seq', (select coalesce(max(id), 1) from program_showperformance));

-- showreview
insert
into public.program_showreview
	(id, uuid, created, updated, show_id, source, rating, body, url)
select
	id, uuid, created, updated, show_id, source, rating, body, url
from tf2018.program_review;

select setval('program_showreview_id_seq', (select coalesce(max(id), 1) from program_showreview));

-- showimage
insert
into public.program_showimage
	(id, uuid, created, updated, show_id, name, image)
select
	id, uuid, created, updated, show_id, name, image
from tf2018.program_showimage;

select setval('program_showimage_id_seq', (select coalesce(max(id), 1) from program_showimage));

/***********/
/* Tickets */
/***********/
-- boxoffice
insert
into tickets_boxoffice
	(id, uuid, created, updated, festival_id, name)
select
	id, uuid, created, updated, 1, name
from tf2018.program_boxoffice;

select setval('tickets_boxoffice_id_seq', (select coalesce(max(id), 1) from tickets_boxoffice));

-- tickettype
insert
into tickets_tickettype
	(id, uuid, created, updated, festival_id, name, seqno, price, is_online, is_admin, rules, payment)
select
	id, uuid, created, updated, 1, name, seqno, price, is_online, is_admin, rules, payment
from tf2018.tickets_tickettype;

select setval('tickets_tickettype_id_seq', (select coalesce(max(id), 1) from tickets_tickettype));

-- fringertype
insert
into tickets_fringertype
	(id, uuid, created, updated, festival_id, name, shows, price, is_online, rules, payment)
select
	id, uuid, created, updated, 1, name, shows, price, is_online, rules, payment
from tf2018.tickets_fringertype;

select setval('tickets_fringertype_id_seq', (select coalesce(max(id), 1) from tickets_fringertype));

-- sale
insert
into tickets_sale
	(id, uuid, created, updated, festival_id, boxoffice_id, customer, user_id, buttons, amount, stripe_fee, completed)
select
	id, uuid, created, updated, 1, box_office_id, customer, user_id, buttons, amount, stripe_fee, completed
from tf2018.tickets_sale;

select setval('tickets_sale_id_seq', (select coalesce(max(id), 1) from tickets_sale));

-- refund
insert
into tickets_refund
	(id, uuid, created, updated, festival_id, boxoffice_id, customer, user_id, reason, amount, completed)
select
	id, uuid, created, updated, 1, box_office_id, customer, user_id, reason, amount, completed
from tf2018.tickets_refund;

select setval('tickets_refund_id_seq', (select coalesce(max(id), 1) from tickets_refund));

-- basket
insert
into tickets_basket
	(uuid, created, updated, user_id)
select
	uuid, created, updated, user_id
from tf2018.tickets_basket;

-- fringer
insert
into tickets_fringer
	(id, uuid, created, updated, user_id, basket_id, sale_id, name, description, shows, cost, payment)
select
	id, uuid, created, updated, user_id, basket_id, sale_id, name, description, shows, cost, payment
from tf2018.tickets_fringer;

select setval('tickets_fringer_id_seq', (select coalesce(max(id), 1) from tickets_fringer));

-- ticket
insert
into tickets_ticket
	(id, uuid, created, updated, user_id, basket_id, sale_id, refund_id, performance_id, description, fringer_id, cost, payment)
select
	id, uuid, created, updated, user_id, basket_id, sale_id, refund_id, performance_id, description, fringer_id, cost, payment
from tf2018.tickets_ticket;

select setval('tickets_ticket_id_seq', (select coalesce(max(id), 1) from tickets_ticket));




