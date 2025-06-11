do $$

declare
	from_festival varchar := 'TF2023';
	from_festival_start date := date '2023-06-22';
	from_festival_id int;
	to_festival varchar := 'TF2024';
	to_festival_start date := date '2024-06-27';
	to_festival_id int;
	
begin

	-- Delete new festival if it already exists
	select id into to_festival_id from core_festival where name = to_festival;
	if to_festival_id is not null then
		delete from volunteers_volunteer_roles where volunteer_id in (select id from core_user where festival_id = to_festival_id);
		delete from volunteers_shift where location_id in (select id from volunteers_location where festival_id = to_festival_id);
		delete from volunteers_location where festival_id = to_festival_id;
		delete from volunteers_role where festival_id = to_festival_id;
		delete from volunteers_volunteer where user_id in (select id from core_user where festival_id = to_festival_id);
		delete from tickets_donation where festival_id = to_festival_id;
		delete from tickets_bucket where show_id in (select id from program_show where festival_id = to_festival_id);
		delete from tickets_payasyouwill where sale_id in (select id from tickets_sale where festival_id = to_festival_id);
		delete from tickets_fringer where type_id in (select id from tickets_fringertype where festival_id = to_festival_id);
		delete from tickets_ticket where type_id in (select id from tickets_tickettype where festival_id = to_festival_id);
		delete from tickets_sale where festival_id = to_festival_id;
		delete from tickets_refund where festival_id = to_festival_id;
		delete from tickets_basket where user_id in (select id from core_user where festival_id = to_festival_id);
		delete from tickets_checkpoint where venue_id in (select id from program_venue where festival_id = to_festival_id);
		delete from tickets_checkpoint where boxoffice_id in (select id from tickets_boxoffice where festival_id = to_festival_id);
		delete from core_user where festival_id = to_festival_id;
		delete from tickets_boxoffice where festival_id = to_festival_id;
		delete from tickets_fringertype where festival_id = to_festival_id;
		delete from tickets_tickettype where festival_id = to_festival_id;
		delete from program_show_genres where show_id in (select id from program_show where festival_id = to_festival_id);
		delete from program_showreview where show_id in (select id from program_show where festival_id = to_festival_id);
		delete from program_showperformance where show_id in (select id from program_show where festival_id = to_festival_id);
		delete from program_showimage where show_id in (select id from program_show where festival_id = to_festival_id);
		delete from program_show where festival_id = to_festival_id;
		delete from program_companycontact where company_id in (select id from program_company where festival_id = to_festival_id);
		delete from program_company where festival_id = to_festival_id;
		delete from program_venuecontact where venue_id in (select id from program_venue where festival_id = to_festival_id);
		delete from program_venuesponsor where venue_id in (select id from program_venue where festival_id = to_festival_id);
		delete from program_venue where festival_id = to_festival_id;
		delete from program_genre where festival_id = to_festival_id;
		delete from content_navigator where festival_id = to_festival_id;
		delete from content_resource where festival_id = to_festival_id;
		delete from content_image where festival_id = to_festival_id;
		delete from content_document where festival_id = to_festival_id;
		delete from content_pageimage where page_id in (select id from content_page where festival_id = to_festival_id);
		delete from content_page where festival_id = to_festival_id;
		delete from core_festival where id = to_festival_id;
	end if;

	-- Get festival to be copied
	select id into strict from_festival_id from core_festival where name = from_festival;
	
	-- Create new festival
	insert
	into	core_festival
			(uuid, created, updated, name, title, venue_map, is_archived, button_price, volunteer_comps)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival, to_festival, '', false, cf.button_price, cf.volunteer_comps
	from	core_festival cf
	where	cf.id = from_festival_id
	returning id into strict to_festival_id;

	-- Copy pages (including images)
	insert
	into	content_page
			(uuid, created, updated, festival_id, name, title, body, body_test)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, cp.name, cp.title, cp.body, ''
	from	content_page cp
	where	cp.festival_id = from_festival_id;
	
	insert
	into	content_pageimage
			(uuid, created, updated, page_id, name, image)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tcp.id, cpi.name, cpi.image
	from	content_page cp
			join content_pageimage cpi on cpi.page_id = cp.id
			join content_page tcp on tcp.festival_id = to_festival_id and tcp.name = cp.name
	where	cp.festival_id = from_festival_id;
	
	-- Copy documents
	insert
	into	content_document
			(uuid, created, updated, festival_id, name, file, filename)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, cd.name, cd.file, cd.filename
	from	content_document cd
	where	cd.festival_id = from_festival_id;
	
	-- Copy images
	insert
	into	content_image
			(uuid, created, updated, festival_id, name, image, map)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, ci.name, ci.image, ci.map
	from	content_image ci
	where	ci.festival_id = from_festival_id;
	
	-- Copy resources
	insert
	into	content_resource
			(uuid, created, updated, festival_id, name, type, body, body_test)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, cr.name, cr.type, cr.body, ''
	from	content_resource cr
	where	cr.festival_id = from_festival_id;
	
	-- Copy navigators
	insert
	into	content_navigator
			(uuid, created, updated, festival_id, seqno, label, type, url, page_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, cn.seqno, cn.label, cn.type, cn.url, tcp.id 
	from	content_navigator cn
			left outer join content_page cp on cp.id = cn.page_id
			left outer join content_page tcp on tcp.festival_id = to_festival_id and tcp.name = cp.name
	where	cn.festival_id = from_festival_id;
	
	-- Program genres
	insert
	into	program_genre
			(uuid, created, updated, festival_id, name)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, pg.name
	from	program_genre pg
	where	pg.festival_id = from_festival_id;
	
	-- Copy venues (including contacts and sponsors)
	insert
	into	program_venue
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram,
			is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, pv.name, pv.image, pv.listing, pv.listing_short, pv.detail,
			pv.address1, pv.address2, pv.city, pv.post_code, pv.telno, pv.email, pv.website, pv.facebook, pv.twitter, pv.instagram,
			pv.is_ticketed, pv.is_scheduled, pv.is_searchable, pv.capacity, pv.map_index, pv.color
	from	program_venue pv
	where	pv.festival_id = from_festival_id;
	
	insert
	into	program_venuecontact
			(uuid, created, updated, venue_id, name, role,
			address1, address2, city, post_code, telno, mobile, email)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpv.id, pvc.name, pvc.role,
			pvc.address1, pvc.address2, pvc.city, pvc.post_code, pvc.telno, pvc.mobile, pvc.email
	from	program_venue pv
			join program_venuecontact pvc on pvc.venue_id = pv.id
			join program_venue tpv on tpv.festival_id = to_festival_id and tpv.name = pv.name
	where	pv.festival_id = from_festival_id;
	
	insert
	into	program_venuesponsor
			(uuid, created, updated, venue_id, name,
			image, color, background, message,
			website, facebook, twitter, instagram, contact, email, telno)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpv.id, pvs.name,
			pvs.image, pvs.color, pvs.background, pvs.message,
			pvs.website, pvs.facebook, pvs.twitter, pvs.instagram, pvs.contact, pvs.email, pvs.telno
	from	program_venue pv
			join program_venuesponsor pvs on pvs.venue_id = pv.id
			join program_venue tpv on tpv.festival_id = to_festival_id and tpv.name = pv.name
	where	pv.festival_id = from_festival_id;
	
	-- Copy companies (including contacts)
	insert
	into	program_company
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, pc.name, pc.image, pc.listing, pc.listing_short, pc.detail,
			pc.address1, pc.address2, pc.city, pc.post_code, pc.telno, pc.email, pc.website, pc.facebook, pc.twitter, pc.instagram
	from	program_company pc
	where	pc.festival_id = from_festival_id;
	
	insert
	into	program_companycontact
			(uuid, created, updated, company_id, name, role,
			address1, address2, city, post_code, telno, mobile, email)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpc.id, pcc.name, pcc.role,
			pcc.address1, pcc.address2, pcc.city, pcc.post_code, pcc.telno, pcc.mobile, pcc.email
	from	program_company pc
			join program_companycontact pcc on pcc.company_id = pc.id
			join program_venue tpc on tpc.festival_id = to_festival_id and tpc.name = pc.name
	where	pc.festival_id = from_festival_id;
	
	-- Program shows (including images, performances and genres)
	insert
	into	program_show
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			company_id, website, facebook, twitter, instagram,
			genre_text, has_warnings, age_range, duration, warnings,
			is_ticketed, is_suspended, is_cancelled, replaced_by_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, ps.name, ps.image, ps.listing, ps.listing_short, ps.detail,
			tpc.id, ps.website, ps.facebook, ps.twitter, ps.instagram,
			ps.genre_text, ps.has_warnings, ps.age_range, ps.duration, ps.warnings,
			ps.is_ticketed, ps.is_suspended, ps.is_cancelled, null
	from	program_show ps
			join program_company pc on pc.id = ps.company_id
			join program_company tpc on tpc.festival_id = to_festival_id and tpc.name = pc.name
	where	ps.festival_id = from_festival_id;
	
	insert
	into	program_showimage
			(uuid, created, updated, show_id, name, image)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tps.id, psi.name, psi.image
	from	program_show ps
			join program_showimage psi on psi.show_id = ps.id
			join program_show tps on tps.festival_id = to_festival_id and tps.name = ps.name
	where	ps.festival_id = from_festival_id;
	
	insert
	into	program_showperformance
			(uuid, created, updated, show_id, venue_id, date, time, audience, notes)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tps.id, tpv.id, to_festival_start + (psp.date - from_festival_start), psp.time, 0, ''
	from	program_show ps
			join program_showperformance psp on psp.show_id = ps.id
			join program_show tps on tps.festival_id = to_festival_id and tps.name = ps.name
			join program_venue pv on pv.id = psp.venue_id
			join program_venue tpv on tpv.festival_id = to_festival_id and tpv.name = pv.name
	where	ps.festival_id = from_festival_id;
	
	insert
	into	program_show_genres
			(show_id, genre_id)
	select	tps.id, tpg.id
	from	program_show ps
			join program_show_genres psg on psg.show_id = ps.id
			join program_genre pg on pg.id = psg.genre_id
			join program_show tps on tps.festival_id = to_festival_id and tps.name = ps.name
			join program_genre tpg on tpg.festival_id = to_festival_id and tpg.name = pg.name
	where	ps.festival_id = from_festival_id;
	
	-- Ticket types
	insert
	into	tickets_tickettype
			(uuid, created, updated, festival_id, name, seqno, price, payment, is_online, is_boxoffice, is_venue, rules)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, tt.name, tt.seqno, tt.price, tt.payment, tt.is_online, tt.is_boxoffice, tt.is_venue, tt.rules
	from	tickets_tickettype as tt
	where	tt.festival_id = from_festival_id;
	
	insert
	into	tickets_fringertype
			(uuid, created, updated, festival_id, name, shows, price, is_online, ticket_type_id, rules)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, tf.name, tf.shows, tf.price, tf.is_online, tttt.id, tf.rules
	from	tickets_fringertype as tf
			join tickets_tickettype ttt on ttt.id = tf.ticket_type_id
			join tickets_tickettype tttt on tttt.festival_id = to_festival_id and tttt.name = ttt.name
	where	tf.festival_id = from_festival_id;
	
	-- Boxoffices
	insert
	into	tickets_boxoffice
			(uuid, created, updated, festival_id, name)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, tb.name
	from	tickets_boxoffice as tb
	where	tb.festival_id = from_festival_id;

	-- Volunteer roles
	insert
	into	volunteers_role
			(uuid, created, updated, festival_id, description, information, comps_per_shift)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, vr.description, vr.information, vr.comps_per_shift
	from	volunteers_role as vr
	where	vr.festival_id = from_festival_id;

	-- Volunteer locations
	insert
	into	volunteers_location
			(uuid, created, updated, festival_id, description, information)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, vl.description, vl.information
	from	volunteers_location as vl
	where	vl.festival_id = from_festival_id;

end $$;
