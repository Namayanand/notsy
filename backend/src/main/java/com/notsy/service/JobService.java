package com.notsy.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.job.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.quartz.*;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class JobService {

    private final Scheduler scheduler;
    private final ObjectMapper objectMapper;

    private static final int MAX_RETRIES = 3;
    private static final long INITIAL_BACKOFF_MS = 1000; // 1 second

    // --- Embedding Job ---

    public void scheduleEmbeddingJob(Long resourceId, Long topicId, String filePath,
                                     String sourceUrl, String fileType, Long userId) {
        try {
            JobDetail job = JobBuilder.newJob(EmbeddingJob.class)
                .withIdentity("embedding_" + resourceId, "embedding")
                .usingJobData("resourceId", resourceId)
                .usingJobData("topicId", topicId)
                .usingJobData("filePath", filePath != null ? filePath : "")
                .usingJobData("sourceUrl", sourceUrl != null ? sourceUrl : "")
                .usingJobData("fileType", fileType != null ? fileType : "")
                .usingJobData("userId", userId)
                .usingJobData("retryCount", MAX_RETRIES)
                .usingJobData("currentRetry", 0)
                .storeDurably()
                .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("embedding_trigger_" + resourceId, "embedding")
                .startNow()
                .build();

            scheduler.scheduleJob(job, trigger);
            log.info("Scheduled embedding job for resource {}", resourceId);
        } catch (SchedulerException e) {
            log.error("Failed to schedule embedding job for resource {}", resourceId, e);
        }
    }

    public void rescheduleWithBackoff(Long resourceId, int currentRetry) {
        if (currentRetry >= MAX_RETRIES) {
            log.error("Max retries reached for embedding job resource {}", resourceId);
            return;
        }

        try {
            long backoffMs = INITIAL_BACKOFF_MS * (long) Math.pow(2, currentRetry);

            JobDetail existingJob = scheduler.getJobDetail(
                new JobKey("embedding_" + resourceId, "embedding"));

            if (existingJob == null) {
                log.warn("Existing job not found for resource {}, cannot reschedule", resourceId);
                return;
            }

            JobDetail newJob = JobBuilder.newJob(EmbeddingJob.class)
                .withIdentity("embedding_" + resourceId + "_retry_" + currentRetry, "embedding")
                .usingJobData(existingJob.getJobDataMap())
                .usingJobData("currentRetry", currentRetry + 1)
                .storeDurably()
                .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("embedding_retry_trigger_" + resourceId + "_" + currentRetry, "embedding")
                .startAt(new Date(System.currentTimeMillis() + backoffMs))
                .build();

            scheduler.scheduleJob(newJob, trigger);
            log.info("Rescheduled embedding job for resource {} with backoff {}ms (retry {}/{})",
                resourceId, backoffMs, currentRetry + 1, MAX_RETRIES);
        } catch (SchedulerException e) {
            log.error("Failed to reschedule embedding job for resource {}", resourceId, e);
        }
    }

    // --- Flashcard Generation Job ---

    public void scheduleFlashcardGeneration(Long conversationId, Long topicId, Long userId) {
        try {
            JobDetail job = JobBuilder.newJob(FlashcardGenerationJob.class)
                .withIdentity("flashcard_" + conversationId, "flashcard")
                .usingJobData("conversationId", conversationId)
                .usingJobData("topicId", topicId)
                .usingJobData("userId", userId)
                .storeDurably()
                .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("flashcard_trigger_" + conversationId, "flashcard")
                .startNow()
                .build();

            scheduler.scheduleJob(job, trigger);
            log.info("Scheduled flashcard generation job for conversation {}", conversationId);
        } catch (SchedulerException e) {
            log.error("Failed to schedule flashcard job for conversation {}", conversationId, e);
        }
    }

    // --- Study Planner Job ---

    public void scheduleStudyPlanner(Long planId, Long userId) {
        try {
            JobDetail job = JobBuilder.newJob(StudyPlannerJob.class)
                .withIdentity("study_planner_" + planId, "study_planner")
                .usingJobData("planId", planId)
                .usingJobData("userId", userId)
                .storeDurably()
                .build();

            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("study_planner_trigger_" + planId, "study_planner")
                .startNow()
                .build();

            scheduler.scheduleJob(job, trigger);
            log.info("Scheduled study planner job for plan {}", planId);
        } catch (SchedulerException e) {
            log.error("Failed to schedule study planner job for plan {}", planId, e);
        }
    }

    // --- Recall Nudge Job (scheduled daily) ---

    public void scheduleRecallNudgeJob(int nudgeDaysThreshold) {
        try {
            JobDetail job = JobBuilder.newJob(RecallNudgeJob.class)
                .withIdentity("recall_nudge", "notifications")
                .usingJobData("nudgeDays", nudgeDaysThreshold)
                .storeDurably()
                .build();

            // Run daily at 9am
            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("recall_nudge_trigger", "notifications")
                .withSchedule(CronScheduleBuilder.cronSchedule("0 0 9 * * ?"))
                .build();

            scheduler.scheduleJob(job, trigger);
            log.info("Scheduled daily recall nudge job");
        } catch (SchedulerException e) {
            log.error("Failed to schedule recall nudge job", e);
        }
    }

    // --- Cancel Job ---

    public void cancelJob(String jobName, String group) {
        try {
            scheduler.deleteJob(new JobKey(jobName, group));
            log.info("Cancelled job {}/{}", group, jobName);
        } catch (SchedulerException e) {
            log.error("Failed to cancel job {}/{}", group, jobName, e);
        }
    }
}
