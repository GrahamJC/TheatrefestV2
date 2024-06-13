do $$

declare
	v_test_festival_id integer;
	v_curr_festival_id integer;

begin

	-- Get site and test/current festivals
	select id into v_test_festival_id from core_festival where name = 'TEST';
	select id into v_curr_festival_id from core_festival where name = 'TF2024';

	-- Delete tickets, PAYW, sales, refunds, checkpoints, efringers and box offices
	delete from tickets_ticket where sale_id in (select id from tickets_sale where festival_id = v_test_festival_id);
	delete from tickets_payasyouwill where sale_id in (select id from tickets_sale where festival_id = v_test_festival_id);
	delete from tickets_fringer where sale_id in (select id from tickets_sale where festival_id = v_test_festival_id);
	delete from tickets_ticket where refund_id in (select id from tickets_refund where festival_id = v_test_festival_id);
	delete from tickets_sale where festival_id = v_test_festival_id;
	delete from tickets_refund where festival_id = v_test_festival_id;
	delete from tickets_checkpoint where boxoffice_id in (select id from tickets_boxoffice where festival_id = v_test_festival_id);
	delete from tickets_checkpoint where venue_id in (select id from program_venue where festival_id = v_test_festival_id);
	delete from tickets_fringer where user_id in (select id from core_user where festival_id = v_test_festival_id);
	delete from tickets_boxoffice where festival_id = v_test_festival_id;

	-- Delete shows, venues and companies
	delete from program_showperformance where show_id in (select id from program_show where festival_id = v_test_festival_id);
	delete from program_show where festival_id = v_test_festival_id;
	delete from program_venue where festival_id = v_test_festival_id;
	delete from program_company where festival_id = v_test_festival_id;

	-- Delete users
	delete from volunteers_volunteer where user_id in (select id from core_user where festival_id = v_test_festival_id);
	delete from tickets_basket where user_id in (select id from core_user where festival_id = v_test_festival_id);
	delete from core_user where festival_id = v_test_festival_id;

	-- Box offices
	insert
	into	tickets_boxoffice
			(uuid, created, updated, festival_id, name)
	values	(uuid_generate_v4(), clock_timestamp(), clock_timestamp(), v_test_festival_id, 'Boxoffice');

	-- Companies
	create temp table tmp_company (
		name varchar(64) not null,
		id integer
	) on commit drop;

	insert into tmp_company (name) values ('Company');

	insert
	into	program_company
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), v_test_festival_id, tc.name, '', '', '', '',
			'', '', '', '', '', '', '', '', '', ''
	from 	tmp_company tc;

	update	tmp_company tc
	set 	id = pc.id
	from 	program_company pc
	where 	pc.festival_id = v_test_festival_id
	and 	pc.name = tc.name;

	-- Venues
	create temp table tmp_venue (
		name varchar(64) not null,
		is_ticketed bool not null,
		id integer
	) on commit drop;

	insert into tmp_venue (name, is_ticketed) values ('Venue A', true);
	insert into tmp_venue (name, is_ticketed) values ('Venue B', true);
	insert into tmp_venue (name, is_ticketed) values ('Venue C', true);
	insert into tmp_venue (name, is_ticketed) values ('Venue D', true);
	insert into tmp_venue (name, is_ticketed) values ('Alt Space A', false);
	insert into tmp_venue (name, is_ticketed) values ('Alt Space B', false);

	insert
	into	program_venue
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram,
			is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), v_test_festival_id, tv.name, '', '', '', '',
			'', '', '', '', '', '', '', '', '', '',
			tv.is_ticketed, true, true, 50, 0, ''
	from 	tmp_venue tv;

	update	tmp_venue tv
	set 	id = pv.id
	from 	program_venue pv
	where 	pv.festival_id = v_test_festival_id
	and 	pv.name = tv.name;

	-- Shows
	create temp table tmp_show (
		name varchar(64) not null,
		company varchar(64) not null,
		venue varchar(64) not null,
		is_ticketed bool not null,
		seqno integer not null,
		id integer
	) on commit drop;

	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show A1', 'Company', 'Venue A', true, 1);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show A2', 'Company', 'Venue A', true, 2);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show A3', 'Company', 'Venue A', true, 3);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show B1', 'Company', 'Venue B', true, 1);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show B2', 'Company', 'Venue B', true, 2);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show B3', 'Company', 'Venue B', true, 3);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show C1', 'Company', 'Venue C', true, 1);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show C2', 'Company', 'Venue C', true, 2);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show C3', 'Company', 'Venue C', true, 3);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show D1', 'Company', 'Venue D', true, 1);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show D2', 'Company', 'Venue D', true, 2);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Show D3', 'Company', 'Venue D', true, 3);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show A1', 'Company', 'Alt Space A', false, 0);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show A2', 'Company', 'Alt Space A', false, 0);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show A3', 'Company', 'Alt Space A', false, 0);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show B1', 'Company', 'Alt Space B', false, 0);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show B2', 'Company', 'Alt Space B', false, 0);
	insert into tmp_show (name, company, venue, is_ticketed, seqno) values ('Alt Show B3', 'Company', 'Alt Space B', false, 0);

	insert
	into	program_show
			(uuid, created, updated, festival_id, name, company_id,
			image, listing, listing_short, detail,
			website, facebook, twitter, instagram,
			genre_text, has_warnings, age_range, duration, warnings,
			is_ticketed, is_suspended, is_cancelled, replaced_by_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), v_test_festival_id, ts.name, tc.id,
			'', '', '', '',
			'', '', '', '',
			'', false, '', 45, '',
			ts.is_ticketed, false, false, null
	from 	tmp_show ts
			join tmp_company tc on tc.name = ts.company;

	update	tmp_show ts
	set 	id = ps.id
	from 	program_show ps
	where 	ps.festival_id = v_test_festival_id
	and 	ps.name = ts.name;

	-- Performances
	create temp table tmp_performance (
		seqno integer not null,
		time time not null
	) on commit drop;

	insert into tmp_performance (seqno, time) values (1, '14:00');
	insert into tmp_performance (seqno, time) values (1, '17:00');
	insert into tmp_performance (seqno, time) values (1, '20:00');
	insert into tmp_performance (seqno, time) values (2, '15:00');
	insert into tmp_performance (seqno, time) values (2, '18:00');
	insert into tmp_performance (seqno, time) values (2, '21:00');
	insert into tmp_performance (seqno, time) values (3, '16:00');
	insert into tmp_performance (seqno, time) values (3, '19:00');
	insert into tmp_performance (seqno, time) values (3, '22:00');

	insert
	into 	program_showperformance
			(uuid, created, updated, show_id, date, time, audience, notes, venue_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), ts.id, current_date, tp.time, 0, '', tv.id
	from 	tmp_show ts
			join tmp_performance tp on tp.seqno = ts.seqno
			join tmp_venue tv on tv.name = ts.venue;

	insert
	into 	program_showperformance
			(uuid, created, updated, show_id, date, time, audience, notes, venue_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), ts.id, current_date + 1, tp.time, 0, '', tv.id
	from 	tmp_show ts
			join tmp_performance tp on tp.seqno = ts.seqno
			join tmp_venue tv on tv.name = ts.venue;

	insert
	into 	program_showperformance
			(uuid, created, updated, show_id, date, time, audience, notes, venue_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), ts.id, current_date + 2, tp.time, 0, '', tv.id
	from 	tmp_show ts
			join tmp_performance tp on tp.seqno = ts.seqno
			join tmp_venue tv on tv.name = ts.venue;

	-- Set online sales and box office open dates
	update core_festival set online_sales_open = current_date, boxoffice_open = current_date where id = v_test_festival_id;

	-- Copy users from current festival
	insert
	into 	core_user
			(uuid, created, updated,
			festival_id, email, password, first_name, last_name,
			is_active, is_superuser, is_admin, is_volunteer, is_boxoffice, is_venue,
			buttons_issued)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(),
			v_test_festival_id, email, password, first_name, last_name,
			is_active, is_superuser, is_admin, is_volunteer, is_boxoffice, is_venue,
			0
	from	core_user
	where 	festival_id = v_curr_festival_id
	and 	is_active = true
	and 	(is_boxoffice = true or is_venue = true);

	insert
	into 	volunteers_volunteer
			(uuid, created, updated, user_id, is_dbs)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tcu.id, cvv.is_dbs
	from	core_user tcu
			join core_user ccu on ccu.festival_id = v_curr_festival_id and ccu.email = tcu.email
			join volunteers_volunteer cvv on cvv.user_id = ccu.id
	where 	tcu.festival_id = v_test_festival_id;

end $$;

