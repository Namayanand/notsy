package com.notsy.job;

import com.notsy.entity.Notification;
import com.notsy.entity.Streak;
import com.notsy.entity.Topic;
import com.notsy.entity.User;
import com.notsy.repository.*;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Component
@Slf4j
public class RecallNudgeJob implements Job {

    @Autowired
    private StreakRepository streakRepository;

    @Autowired
    private TopicRepository topicRepository;

    @Autowired
    private NotificationRepository notificationRepository;

    @Autowired
    private UserRepository userRepository;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        int nudgeDays = context.getJobDetail().getJobDataMap().getInt("nudgeDays");

        log.info("Executing RecallNudgeJob for topics not reviewed in {} days", nudgeDays);

        try {
            LocalDate cutoffDate = LocalDate.now().minusDays(nudgeDays);

            // Find all topic streaks needing nudge
            List<Streak> streaks = streakRepository.findGlobalStreaksNeedingNudge(cutoffDate);

            for (Streak streak : streaks) {
                long daysSinceReview = ChronoUnit.DAYS.between(streak.getLastReviewDate(), LocalDate.now());
                User user = streak.getUser();
                Topic topic = streak.getTopic();

                if (topic != null) {
                    // Send nudge notification
                    Notification nudge = Notification.builder()
                        .user(user)
                        .type(Notification.NotificationType.REVIEW_NUDGE)
                        .title("Time to review " + topic.getTitle())
                        .message(String.format(
                            "You haven't reviewed '%s' in %d days. " +
                            "A quick review will help consolidate your knowledge!",
                            topic.getTitle(), daysSinceReview))
                        .topicId(topic.getId())
                        .notebookId(topic.getNotebook() != null ? topic.getNotebook().getId() : null)
                        .build();
                    notificationRepository.save(nudge);
                    log.info("Sent review nudge for topic {} to user {}", topic.getId(), user.getId());
                }
            }

            // Also check per-topic streaks
            List<Topic> allTopics = topicRepository.findAll();
            for (Topic topic : allTopics) {
                if (topic.getNotebook() != null && topic.getNotebook().getUser() != null) {
                    User owner = topic.getNotebook().getUser();
                    streakRepository.findByUserIdAndTopic_Id(owner.getId(), topic.getId())
                        .ifPresent(streak -> {
                            if (streak.getLastReviewDate() != null &&
                                streak.getLastReviewDate().isBefore(cutoffDate)) {
                                long daysSince = ChronoUnit.DAYS.between(streak.getLastReviewDate(), LocalDate.now());
                                Notification nudge = Notification.builder()
                                    .user(owner)
                                    .type(Notification.NotificationType.REVIEW_NUDGE)
                                    .title("Review reminder: " + topic.getTitle())
                                    .message(String.format(
                                        "It's been %d days since you reviewed '%s'. Time for a quick refresher?",
                                        daysSince, topic.getTitle()))
                                    .topicId(topic.getId())
                                    .notebookId(topic.getNotebook().getId())
                                    .build();
                                notificationRepository.save(nudge);
                            }
                        });
                }
            }

            log.info("RecallNudgeJob completed, sent {} notifications", streaks.size());
        } catch (Exception e) {
            log.error("RecallNudgeJob failed: {}", e.getMessage());
            throw new JobExecutionException(e);
        }
    }
}
