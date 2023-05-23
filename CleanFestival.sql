@set festival_id = 0

begin;

-- Delete tickets, sales, refunds, checkpoints and efringers
delete from tickets_ticket where sale_id in (select id from tickets_sale where festival_id = :festival_id);
delete from tickets_ticket where refund_id in (select id from tickets_refund where festival_id = :festival_id);
delete from tickets_sale where festival_id = :festival_id;
delete from tickets_refund where festival_id = :festival_id;
delete from tickets_checkpoint where boxoffice_id in (select id from tickets_boxoffice where festival_id = :festival_id);
delete from tickets_checkpoint where venue_id in (select id from program_venue where festival_id = :festival_id);
delete from tickets_fringer where user_id in (select id from core_user where festival_id = :festival_id);

-- Delete shows
delete from program_show_genres where show_id in (select id from program_show where festival_id = :festival_id);
delete from program_showperformance where show_id in (select id from program_show where festival_id = :festival_id);
delete from program_showimage where show_id in (select id from program_show where festival_id = :festival_id);
delete from program_showreview where show_id in (select id from program_show where festival_id = :festival_id);
delete from program_show where festival_id = :festival_id;
delete from program_genre where festival_id = :festival_id;

-- Delete companies
delete from program_companycontact where company_id in (select id from program_company where festival_id = :festival_id);
delete from program_company where festival_id = :festival_id;

-- Delete venues
delete from program_venuecontact where venue_id in (select id from program_venue where festival_id = :festival_id);
delete from program_venuesponsor where venue_id in (select id from program_venue where festival_id = :festival_id);
delete from program_venue where festival_id = :festival_id;

-- Delete content
delete from content_document where festival_id = :festival_id;
delete from content_image where festival_id = :festival_id and name not in ('Banner', 'BannerMobile');
delete from content_pageimage where page_id in (select id from content_page where festival_id = :festival_id and name not in ('Home'));
delete from content_page where festival_id = :festival_id and name not in ('Home');
delete from content_resource where festival_id = :festival_id and name not in ('Stylesheet');

rollback;
