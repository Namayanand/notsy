package com.notsy.job;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.entity.StudyPlan;
import com.notsy.entity.StudyPlanDay;
import com.notsy.repository.StudyPlanRepository;
import com.notsy.repository.StudyPlanDayRepository;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class StudyPlannerJob implements Job {

    @Autowired
    private StudyPlanRepository studyPlanRepository;

    @Autowired
    private StudyPlanDayRepository studyPlanDayRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private static final String AI_SERVICE_URL = System.getenv("AI_SERVICE_URL") != null
        ? System.getenv("AI_SERVICE_URL") : "http://localhost:8000";

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        Long planId = context.getJobDetail().getJobDataMap().getLong("planId");
        Long userId = context.getJobDetail().getJobDataMap().getLong("userId");

        log.info("Executing StudyPlannerJob for plan {} user {}", planId, userId);

        try {
            StudyPlan plan = studyPlanRepository.findByIdWithDays(planId).orElse(null);
            if (plan == null) {
                throw new JobExecutionException("Study plan not found");
            }

            // Build comprehensive prompt for 3-agent orchestration
            String prompt = buildPlannerPrompt(plan);

            RestTemplate restTemplate = new RestTemplate();
            Map<String, Object> requestBody = Map.of(
                "prompt", prompt,
                "mode", "study_planner",
                "plan_id", planId,
                "user_id", userId
            );

            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.postForObject(
                AI_SERVICE_URL + "/multi_agent/study_planner",
                requestBody,
                Map.class
            );

            if (response != null && response.get("schedule") != null) {
                String scheduleJson = objectMapper.writeValueAsString(response.get("schedule"));
                plan.setStudyScheduleJson(scheduleJson);
                studyPlanRepository.save(plan);

                // Parse and save individual days
                parseAndSaveDays(plan, (List<Map<String, Object>>) response.get("schedule"));
                log.info("Study plan {} generated successfully", planId);
            }
        } catch (Exception e) {
            log.error("StudyPlannerJob failed for plan {}: {}", planId, e.getMessage());
            throw new JobExecutionException(e);
        }
    }

    private String buildPlannerPrompt(StudyPlan plan) {
        return String.format(
            "Create a day-by-day study plan titled '%s'. Goal: %s. Exam date: %s. Days available: %d. " +
            "Return JSON schedule with structure: [{\"day\": 1, \"date\": \"YYYY-MM-DD\", \"focus\": \"...\", " +
            "\"topics\": [...], \"hours\": 2.0}]",
            plan.getTitle(), plan.getGoalDescription(), plan.getExamDate(), plan.getDaysAvailable()
        );
    }

    private void parseAndSaveDays(StudyPlan plan, List<Map<String, Object>> schedule) {
        LocalDate startDate = plan.getExamDate() != null
            ? plan.getExamDate().minusDays(plan.getDaysAvailable())
            : LocalDate.now();

        for (Map<String, Object> dayData : schedule) {
            int dayNum = ((Number) dayData.get("day")).intValue();
            Object topicsObj = dayData.get("topics");
            String topicsJson = topicsObj instanceof List
                ? topicsObj.toString()
                : (String) topicsObj;

            StudyPlanDay day = StudyPlanDay.builder()
                .plan(plan)
                .dayNumber(dayNum)
                .date(startDate.plusDays(dayNum - 1))
                .focus((String) dayData.get("focus"))
                .topicsJson(topicsJson)
                .hoursPlanned(((Number) dayData.getOrDefault("hours", 2.0)).floatValue())
                .orderIndex(dayNum)
                .build();
            studyPlanDayRepository.save(day);
        }
    }

    // RestTemplate dependency - create inline
    private static class RestTemplate {
        public <T> T postForObject(String url, Object request, Class<T> responseType) {
            try {
                java.net.URI uri = new java.net.URI(url);
                java.net.HttpURLConnection conn = (java.net.HttpURLConnection) uri.toURL().openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(30000);
                conn.setReadTimeout(60000);

                try (var os = conn.getOutputStream()) {
                    var json = new ObjectMapper().writeValueAsString(request);
                    os.write(json.getBytes());
                }

                int status = conn.getResponseCode();
                if (status == 200) {
                    try (var br = new java.io.BufferedReader(new java.io.InputStreamReader(conn.getInputStream()))) {
                        StringBuilder response = new StringBuilder();
                        String line;
                        while ((line = br.readLine()) != null) {
                            response.append(line);
                        }
                        return new com.fasterxml.jackson.databind.ObjectMapper().readValue(response.toString(), responseType);
                    }
                }
            } catch (Exception e) {
                log.error("HTTP request failed: {}", e.getMessage());
            }
            return null;
        }
    }
}
