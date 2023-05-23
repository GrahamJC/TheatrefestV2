@set from_festival_id = 5
@set to_festival_id = 7

rollback;

begin;

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

commit;
