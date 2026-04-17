package com.notsy.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.CreateStudyPlanRequest;
import com.notsy.dto.response.StudyPlanResponse;
import com.notsy.dto.response.StudyPlanDayResponse;
import com.notsy.entity.*;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.StudyPlanRepository;
import com.notsy.repository.StudyPlanDayRepository;
import com.notsy.repository.TopicRepository;
import com.notsy.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class StudyPlanService {

    private final StudyPlanRepository studyPlanRepository;
    private final StudyPlanDayRepository studyPlanDayRepository;
    private final TopicRepository topicRepository;
    private final UserRepository userRepository;
    private final JobService jobService;
    private final ObjectMapper objectMapper;

    @Transactional
    public StudyPlanResponse createStudyPlan(CreateStudyPlanRequest request, User user) {
        StudyPlan plan = StudyPlan.builder()
            .title(request.getTitle())
            .goalDescription(request.getGoalDescription())
            .examDate(request.getExamDate())
            .daysAvailable(request.getDaysAvailable())
            .user(user)
            .isCompleted(false)
            .build();

        plan = studyPlanRepository.save(plan);

        // Collect topic data for the AI planner
        List<Map<String, Object>> topicData = new ArrayList<>();
        if (request.getTopicIds() != null) {
            for (Long topicId : request.getTopicIds()) {
                Topic topic = topicRepository.findByIdAndUserId(topicId, user.getId()).orElse(null);
                if (topic != null) {
                    topicData.add(Map.of(
                        "id", topic.getId(),
                        "title", topic.getTitle() != null ? topic.getTitle() : "",
                        "description", topic.getDescription() != null ? topic.getDescription() : ""
                    ));
                }
            }
        }

        // Collect quiz history (weak spots)
        Map<String, Object> quizHistory = collectQuizHistory(user.getId(), request.getTopicIds());

        // Schedule async job for AI planning
        jobService.scheduleStudyPlanner(plan.getId(), user.getId());

        log.info("Created study plan {} for user {}, AI planner job scheduled", plan.getId(), user.getId());

        return toResponse(plan);
    }

    @Transactional(readOnly = true)
    public List<StudyPlanResponse> getActivePlans(User user) {
        return studyPlanRepository.findActiveByUserId(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<StudyPlanResponse> getAllPlans(User user) {
        return studyPlanRepository.findByUserIdOrderByCreatedAtDesc(user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public StudyPlanResponse getPlan(Long planId, User user) {
        StudyPlan plan = studyPlanRepository.findByIdWithDays(planId)
            .orElseThrow(() -> new ResourceNotFoundException("StudyPlan", planId));

        if (!plan.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("StudyPlan", planId);
        }

        return toResponse(plan);
    }

    @Transactional
    public StudyPlanResponse updatePlanDay(Long planId, Long dayId, String notes, Float hoursCompleted, Boolean isCompleted, User user) {
        StudyPlan plan = studyPlanRepository.findById(planId)
            .orElseThrow(() -> new ResourceNotFoundException("StudyPlan", planId));

        if (!plan.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("StudyPlan", planId);
        }

        StudyPlanDay day = studyPlanDayRepository.findById(dayId)
            .orElseThrow(() -> new ResourceNotFoundException("StudyPlanDay", dayId));

        if (notes != null) day.setNotes(notes);
        if (hoursCompleted != null) day.setHoursCompleted(hoursCompleted);
        if (isCompleted != null) {
            day.setIsCompleted(isCompleted);
            if (isCompleted) {
                day.setCompletedAt(java.time.LocalDateTime.now());
            }
        }

        studyPlanDayRepository.save(day);

        // Check if all days completed
        List<StudyPlanDay> allDays = studyPlanDayRepository.findByPlanIdOrderByDayNumberAscOrderIndexAsc(planId);
        boolean allDone = allDays.stream().allMatch(d -> d.getIsCompleted());
        if (allDone) {
            plan.setIsCompleted(true);
            studyPlanRepository.save(plan);
        }

        return getPlan(planId, user);
    }

    private Map<String, Object> collectQuizHistory(Long userId, List<Long> topicIds) {
        // Placeholder - in real implementation would query quiz repository
        // Returns weak areas per topic
        return Map.of("topics", topicIds != null ? topicIds : List.of(), "weak_areas", List.of());
    }

    private StudyPlanResponse toResponse(StudyPlan plan) {
        List<StudyPlanDayResponse> dayResponses = new ArrayList<>();
        if (plan.getDays() != null) {
            for (StudyPlanDay day : plan.getDays()) {
                List<String> topics = parseTopics(day.getTopicsJson());
                dayResponses.add(StudyPlanDayResponse.builder()
                    .id(day.getId())
                    .dayNumber(day.getDayNumber())
                    .date(day.getDate())
                    .focus(day.getFocus())
                    .topics(topics)
                    .hoursPlanned(day.getHoursPlanned())
                    .hoursCompleted(day.getHoursCompleted())
                    .isCompleted(day.getIsCompleted())
                    .notes(day.getNotes())
                    .build());
            }
        }

        return StudyPlanResponse.builder()
            .id(plan.getId())
            .title(plan.getTitle())
            .goalDescription(plan.getGoalDescription())
            .examDate(plan.getExamDate())
            .daysAvailable(plan.getDaysAvailable())
            .days(dayResponses)
            .isCompleted(plan.getIsCompleted())
            .createdAt(plan.getCreatedAt())
            .build();
    }

    private List<String> parseTopics(String topicsJson) {
        if (topicsJson == null || topicsJson.isEmpty()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(topicsJson, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            return List.of(topicsJson);
        }
    }
}
