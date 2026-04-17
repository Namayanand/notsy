package com.notsy.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.quartz.SchedulerFactoryBean;

import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Autowired;

@Configuration
public class QuartzConfig {

    @Autowired
    private DataSource dataSource;

    @Bean
    public SchedulerFactoryBean schedulerFactoryBean() {
        SchedulerFactoryBean factory = new SchedulerFactoryBean();
        factory.setDataSource(dataSource);
        factory.setOverwriteExistingJobs(true);
        factory.setAutoStartup(true);
        factory.setWaitForJobsToCompleteOnShutdown(true);
        return factory;
    }
}
