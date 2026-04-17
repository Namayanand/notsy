package com.notsy.service;

import com.notsy.dto.response.NotificationResponse;
import com.notsy.entity.Notification;
import com.notsy.entity.User;
import com.notsy.repository.NotificationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class NotificationService {

    private final NotificationRepository notificationRepository;

    @Transactional(readOnly = true)
    public List<NotificationResponse> getNotifications(User user) {
        return notificationRepository.findByUserIdOrderByCreatedAtDesc(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<NotificationResponse> getUnreadNotifications(User user) {
        return notificationRepository.findUnreadByUserId(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public long getUnreadCount(User user) {
        return notificationRepository.countByUserIdAndIsReadFalse(user.getId());
    }

    @Transactional
    public NotificationResponse markAsRead(Long notificationId, User user) {
        Notification notification = notificationRepository.findById(notificationId)
            .orElseThrow(() -> new com.notsy.exception.ResourceNotFoundException("Notification", notificationId));

        if (!notification.getUser().getId().equals(user.getId())) {
            throw new com.notsy.exception.ResourceNotFoundException("Notification", notificationId);
        }

        notification.setIsRead(true);
        notification.setReadAt(LocalDateTime.now());
        notification = notificationRepository.save(notification);
        return toResponse(notification);
    }

    @Transactional
    public void markAllAsRead(User user) {
        List<Notification> unread = notificationRepository.findByUserIdAndIsReadFalseOrderByCreatedAtDesc(user.getId());
        for (Notification n : unread) {
            n.setIsRead(true);
            n.setReadAt(LocalDateTime.now());
        }
        notificationRepository.saveAll(unread);
    }

    @Transactional
    public void sendNotification(User user, Notification.NotificationType type,
                               String title, String message,
                               Long notebookId, Long topicId) {
        Notification notification = Notification.builder()
            .user(user)
            .type(type)
            .title(title)
            .message(message)
            .notebookId(notebookId)
            .topicId(topicId)
            .isRead(false)
            .build();
        notificationRepository.save(notification);
        log.info("Sent {} notification to user {}: {}", type, user.getId(), title);
    }

    @Transactional
    public void deleteNotification(Long notificationId, User user) {
        Notification notification = notificationRepository.findById(notificationId)
            .orElseThrow(() -> new com.notsy.exception.ResourceNotFoundException("Notification", notificationId));

        if (!notification.getUser().getId().equals(user.getId())) {
            throw new com.notsy.exception.ResourceNotFoundException("Notification", notificationId);
        }

        notificationRepository.delete(notification);
    }

    private NotificationResponse toResponse(Notification n) {
        return NotificationResponse.builder()
            .id(n.getId())
            .type(n.getType().name())
            .title(n.getTitle())
            .message(n.getMessage())
            .topicId(n.getTopicId())
            .notebookId(n.getNotebookId())
            .isRead(n.getIsRead())
            .readAt(n.getReadAt())
            .createdAt(n.getCreatedAt())
            .build();
    }
}
