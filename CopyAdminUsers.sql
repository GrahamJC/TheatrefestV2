@set from_festivalid = 0
@set to_festival_id = 0

begin;

insert
into 	core_user 
		(uuid, created, updated,
		site_id, festival_id, email, password, first_name, last_name,
		is_active, is_superuser, is_admin, is_volunteer, is_boxoffice, is_venue)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(),
		site_id, :to_festival_id, email, password, first_name, last_name,
		is_active, is_superuser, is_admin, is_volunteer, is_boxoffice, is_venue
from	core_user
where 	festival_id = :from_festival_id
and 	is_admin = true;

insert 
into 	volunteers_volunteer 
		(uuid, created, updated, user_id, is_dbs)
select	uuid_generate_v4(), clock_timestamp(), clock_timestamp(), tcu.id, fvv.is_dbs
from	core_user tcu
		join core_user fcu on fcu.festival_id = :from_festival_id and fcu.email = tcu.email
		join volunteers_volunteer fvv on fvv.user_id = fcu.id
where 	tcu.festival_id = :to_festival_id;

rollback;
