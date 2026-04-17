package com.notsy.config;

import com.notsy.service.JobService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class AppInitializer {

    private final JobService jobService;

    @Bean
    public ApplicationRunner initializeJobs() {
        return args -> {
            log.info("Initializing scheduled jobs...");
            // Schedule daily recall nudge for topics not reviewed in 7 days
            jobService.scheduleRecallNudgeJob(7);
            log.info("Scheduled recall nudge job (every day at 9am, for topics not reviewed in 7+ days)");
        };
    }
}
