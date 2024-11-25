do $$

declare
    -- New festival details
	festival_name varchar := 'TF2025';
	festival_title varchar := 'Theatrefest 2025';
    online_open date := date '2025-06-01';
    online_close date := date '2025-06-29';
    boxoffice_open date := date '2025-06-23';
    boxoffice_close date := date '2025-06-29';
	
    -- Working variables
	template_id int;
	festival_id int;

begin
	
	-- Get festival template
	select id into strict template_id from core_festival where name = 'Template';
	
	-- Create new festival
	insert
	into	core_festival
			(uuid, created, updated, name, title,
            online_open, online_close, boxoffice_open, boxoffice_close,
            venue_map, is_archived, button_price, volunteer_comps)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_name, festival_title,
            online_open, online_close, boxoffice_open, boxoffice_close,
            '', false, cf.button_price, cf.volunteer_comps
	from	core_festival cf
	where	cf.id = template_id
	returning id into strict festival_id;
	
	-- Copy ticket and fringer types from template
	insert
	into	tickets_tickettype
			(uuid, created, updated, festival_id, name, seqno, price, payment, is_online, is_boxoffice, is_venue, rules)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, name, tt.seqno, tt.price, tt.payment, tt.is_online, tt.is_boxoffice, tt.is_venue, tt.rules
	from	tickets_tickettype as tt
	where	tt.festival_id = template_id;
	
	insert
	into	tickets_fringertype
			(uuid, created, updated, festival_id, name, shows, price, is_online, ticket_type_id, rules)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), to_festival_id, tf.name, tf.shows, tf.price, tf.is_online, tttt.id, tf.rules
	from	tickets_fringertype as tf
			join tickets_tickettype ttt on ttt.id = tf.ticket_type_id
			join tickets_tickettype ftt on ftt.festival_id = festival_id and ftt.name = ttt.name
	where	tf.festival_id = template_id;

    -- Copy navigators from template
	insert
	into	content_navigator
			(uuid, created, updated, festival_id, seqno, label, type, url, page_id)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, cn.seqno, cn.label, cn.type, cn.url, tcp.id 
	from	content_navigator cn
			left outer join content_page cp on cp.id = cn.page_id
			left outer join content_page tcp on tcp.festival_id = festival_id and tcp.name = cp.name
	where	cn.festival_id = template_id;


	-- Copy pages (including images) from template
	insert
	into	content_page
			(uuid, created, updated, festival_id, name, title, body, body_test)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, cp.name, cp.title, cp.body, ''
	from	content_page cp
	where	cp.festival_id = template_id;
	
	insert
	into	content_pageimage
			(uuid, created, updated, page_id, name, image)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tcp.id, cpi.name, cpi.image
	from	content_page cp
			join content_pageimage cpi on cpi.page_id = cp.id
			join content_page tcp on tcp.festival_id = festival_id and tcp.name = cp.name
	where	cp.festival_id = template_id;
	
	-- Copy documents, images and resources from template
	insert
	into	content_document
			(uuid, created, updated, festival_id, name, file, filename)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, cd.name, cd.file, cd.filename
	from	content_document cd
	where	cd.festival_id = template_id;
	
	insert
	into	content_image
			(uuid, created, updated, festival_id, name, image, map)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, ci.name, ci.image, ci.map
	from	content_image ci
	where	ci.festival_id = template_id;
	
	insert
	into	content_resource
			(uuid, created, updated, festival_id, name, type, body, body_test)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, cr.name, cr.type, cr.body, ''
	from	content_resource cr
	where	cr.festival_id = template_id;

    -- Copy genres from template
	insert
	into	program_genre
			(uuid, created, updated, festival_id, name)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, pg.name
	from	program_genre pg
	where	pg.festival_id = template_id;

	-- Copy boxoffices from template
	insert
	into	tickets_boxoffice
			(uuid, created, updated, festival_id, name)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, name
	from	tickets_boxoffice as tb
	where	tb.festival_id = template_id;
	
	-- Copy venues from template
	insert
	into	program_venue
			(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
			address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram,
			is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), festival_id, pv.name, pv.image, pv.listing, pv.listing_short, pv.detail,
			pv.address1, pv.address2, pv.city, pv.post_code, pv.telno, pv.email, pv.website, pv.facebook, pv.twitter, pv.instagram,
			pv.is_ticketed, pv.is_scheduled, pv.is_searchable, pv.capacity, pv.map_index, pv.color
	from	program_venue pv
	where	pv.festival_id = template_id;
	
	insert
	into	program_venuecontact
			(uuid, created, updated, venue_id, name, role,
			address1, address2, city, post_code, telno, mobile, email)
	select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpv.id, pvc.name, pvc.role,
			pvc.address1, pvc.address2, pvc.city, pvc.post_code, pvc.telno, pvc.mobile, pvc.email
	from	program_venue pv
			join program_venuecontact pvc on pvc.venue_id = pv.id
			join program_venue tpv on tpv.festival_id = festival_id and tpv.name = pv.name
	where	pv.festival_id = template_id;

end $$;
