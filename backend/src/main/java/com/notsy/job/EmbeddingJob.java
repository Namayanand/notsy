package com.notsy.job;

import com.notsy.service.AIProxyService;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class EmbeddingJob implements Job {

    @Autowired
    private AIProxyService aiProxyService;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        Long resourceId = context.getJobDetail().getJobDataMap().getLong("resourceId");
        Long topicId = context.getJobDetail().getJobDataMap().getLong("topicId");
        String filePath = context.getJobDetail().getJobDataMap().getString("filePath");
        String sourceUrl = context.getJobDetail().getJobDataMap().getString("sourceUrl");
        String fileType = context.getJobDetail().getJobDataMap().getString("fileType");
        Long userId = context.getJobDetail().getJobDataMap().getLong("userId");

        int maxRetries = context.getJobDetail().getJobDataMap().getInt("retryCount");
        int currentRetry = context.getJobDetail().getJobDataMap().getInt("currentRetry");

        log.info("Executing EmbeddingJob for resource {} (retry {}/{})", resourceId, currentRetry, maxRetries);

        try {
            aiProxyService.embedResource(resourceId, topicId, filePath, sourceUrl, fileType, userId);
        } catch (Exception e) {
            log.error("EmbeddingJob failed for resource {}: {}", resourceId, e.getMessage());
            throw new JobExecutionException(e);
        }
    }
}
