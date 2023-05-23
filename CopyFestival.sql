-- Copy festival
-- =============

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
		(uuid, created, updated, festival_id, name, image, map)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, ci.name, ci.image, ci.map
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

-- Program companies (including contacts)
insert
into	program_company
		(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
		address1, address2, city, post_code, telno, email, website, facebook, twitter, instagram)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, pc.name, pc.image, pc.listing, pc.listing_short, pc.detail,
		pc.address1, pc.address2, pc.city, pc.post_code, pc.telno, pc.email, pc.website, pc.facebook, pc.twitter, pc.instagram
from	program_company pc
where	pc.festival_id = :from_festival_id;

insert
into	program_companycontact
		(uuid, created, updated, company_id, name, role,
		address1, address2, city, post_code, telno, mobile, email)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tpc.id, pcc.name, pcc.role,
		pcc.address1, pcc.address2, pcc.city, pcc.post_code, pcc.telno, pcc.mobile, pcc.email
from	program_company pc
		join program_companycontact pcc on pcc.company_id = pc.id
		join program_venue tpc on tpc.festival_id = :to_festival_id and tpc.name = pc.name
where	pc.festival_id = :from_festival_id;

-- Program shows (including images, performances and genres)
insert
into	program_show
		(uuid, created, updated, festival_id, name, image, listing, listing_short, detail,
		company_id, venue_id, website, facebook, twitter, instagram,
		genre_text, has_warnings, age_range, duration, warnings,
		is_suspended, is_cancelled, replaced_by_id)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, ps.name, ps.image, ps.listing, ps.listing_short, ps.detail,
		tpc.id, tpv.id, ps.website, ps.facebook, ps.twitter, ps.instagram,
		ps.genre_text, ps.has_warnings, ps.age_range, ps.duration, ps.warnings,
		ps.is_suspended, ps.is_cancelled, null
from	program_show ps
		join program_company pc on pc.id = ps.company_id
		join program_company tpc on tpc.festival_id = :to_festival_id and tpc.name = pc.name
		join program_venue pv on pv.id = ps.venue_id
		join program_venue tpv on tpv.festival_id = :to_festival_id and tpv.name = pv.name
where	ps.festival_id = :from_festival_id;

insert
into	program_showimage
		(uuid, created, updated, show_id, name, image)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tps.id, psi.name, psi.image
from	program_show ps
		join program_showimage psi on psi.show_id = ps.id
		join program_show tps on tps.festival_id = :to_festival_id and tps.name = ps.name
where	ps.festival_id = :from_festival_id;

insert
into	program_showperformance
		(uuid, created, updated, show_id, date, time, audience, notes)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tps.id, psp.date, psp.time, 0, ''
from	program_show ps
		join program_showperformance psp on psp.show_id = ps.id
		join program_show tps on tps.festival_id = :to_festival_id and tps.name = ps.name
where	ps.festival_id = :from_festival_id;

insert
into	program_show_genres
		(show_id, genre_id)
select	tps.id, tpg.id
from	program_show ps
		join program_show_genres psg on psg.show_id = ps.id
		join program_genre pg on pg.id = psg.genre_id
		join program_show tps on tps.festival_id = :to_festival_id and tps.name = ps.name
		join program_genre tpg on tpg.festival_id = :to_festival_id and tpg.name = pg.name
where	ps.festival_id = :from_festival_id;

-- Ticket types
insert
into	tickets_tickettype
		(uuid, created, updated, festival_id, name, seqno, price, is_online, is_admin, rules, payment)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, name, tt.seqno, tt.price, tt.is_online, tt.is_admin, tt.rules, tt.payment
from	tickets_tickettype as tt
where	tt.festival_id = :from_festival_id;

insert
into	tickets_fringertype
		(uuid, created, updated, festival_id, name, shows, price, is_online, rules, payment)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, name, tf.shows, tf.price, tf.is_online, tf.rules, tf.payment
from	tickets_fringertype as tf
where	tf.festival_id = :from_festival_id;

-- Boxoffices
insert
into	tickets_boxoffice
		(uuid, created, updated, festival_id, name)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), :to_festival_id, name
from	tickets_boxoffice as tb
where	tb.festival_id = :from_festival_id;

rollback;

