"""
# task for the keno game


    def schedule_round(self):
        # Schedule a new round every 60 seconds
        def job():
            self.current_round = self.create_new_round()
            scheduler.add_job(
                lambda: self.generate_numbers(self.current_round['round_id']),
                'date',
                run_date=self.current_round['timestamp'] + timedelta(seconds=RESULT_GENERATION_TIME),
                id=f"generate_numbers_{self.current_round['round_id']}",
                replace_existing=True
            )

        scheduler.add_job(
            job,
            'interval',
            seconds=ROUND_DURATION,
            id='keno_round',
            next_run_time=datetime.now(timezone.utc),
            replace_existing=True
        )

"""