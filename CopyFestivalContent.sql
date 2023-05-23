-- Copy festival content
-- =====================

@set from_festival_id = 0
@set to_festival_id = 0

begin;

-- Pages (including images)
insert
into	content_page
		(uuid, created, updated, festival_id, name, title, body, body_test)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, cp.name, cp.title, cp.body, ''
from	content_page cp
where	cp.festival_id = :from_festival_id;

insert
into	content_pageimage
		(uuid, created, updated, page_id, name, image)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tcp.id, cpi.name, cpi.image
from	content_page cp
		join content_pageimage cpi on cpi.page_id = cp.id
		join content_page tcp on tcp.festival_id = :to_festival_id and tcp.name = cp.name
where	cp.festival_id = :from_festival_id;

-- Documents
insert
into	content_document
		(uuid, created, updated, festival_id, name, file, filename)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, cd.name, cd.file, cd.filename
from	content_document cd
where	cd.festival_id = :from_festival_id;

-- Images
insert
into	content_image
		(uuid, created, updated, festival_id, name, image)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, ci.name, ci.image
from	content_image ci
where	ci.festival_id = :from_festival_id;

-- Resources
insert
into	content_resource
		(uuid, created, updated, festival_id, name, type, body, body_test)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, cr.name, cr.type, cr.body, ''
from	content_resource cr
where	cr.festival_id = :from_festival_id;

-- Navigators
insert
into	content_navigator
		(uuid, created, updated, festival_id, seqno, label, type, url, page_id)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, cn.seqno, cn.label, cn.type, cn.url, tcp.id 
from	content_navigator cn
		left outer join content_page cp on cp.id = cn.page_id
		left outer join content_page tcp on tcp.festival_id = :to_festival_id and tcp.name = cp.name
where	cn.festival_id = :from_festival_id;

-- Program genres
insert
into	program_genre
		(uuid, created, updated, festival_id, name)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, pg.name
from	program_genre pg
where	pg.festival_id = :from_festival_id;

-- Program venues (including contacts and sponsors)
insert
into	program_venue
		(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
		address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram,
		is_ticketed, is_scheduled, is_searchable, capacity, map_index, color)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, pv.name, pv.image, pv.listing, pv.listing_short, pv.detail,
		pv.address1, pv.address2, pv.city, pv.post_code, pv.telno, pv.email, pv.website, pv.facebook, pv.twitter, pv.instagram,
		pv.is_ticketed, pv.is_scheduled, pv.is_searchable, pv.capacity, pv.map_index, pv.color
from	program_venue pv
where	pv.festival_id = :from_festival_id;

insert
into	program_venuecontact
		(uuid, created, updated, venue_id, name, role,
		address1, address2, city, post_code, telno, mobile, email)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpv.id, pvc.name, pvc.role,
		pvc.address1, pvc.address2, pvc.city, pvc.post_code, pvc.telno, pvc.mobile, pvc.email
from	program_venue pv
		join program_venuecontact pvc on pvc.venue_id = pv.id
		join program_venue tpv on tpv.festival_id = :to_festival_id and tpv.name = pv.name
where	pv.festival_id = :from_festival_id;

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
		join program_venue tpv on tpv.festival_id = :to_festival_id and tpv.name = pv.name
where	pv.festival_id = :from_festival_id;

rollback;

