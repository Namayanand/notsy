package com.notsy.controller;

import com.notsy.entity.User;
import com.notsy.dto.request.CreateStudyPlanRequest;
import com.notsy.dto.response.StudyPlanResponse;
import com.notsy.service.StudyPlanService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/study-plans")
@RequiredArgsConstructor
public class StudyPlanController {

    private final StudyPlanService studyPlanService;

    @PostMapping
    public ResponseEntity<StudyPlanResponse> createStudyPlan(
            @Valid @RequestBody CreateStudyPlanRequest request,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(studyPlanService.createStudyPlan(request, user));
    }

    @GetMapping
    public ResponseEntity<List<StudyPlanResponse>> getActivePlans(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(studyPlanService.getActivePlans(user));
    }

    @GetMapping("/all")
    public ResponseEntity<List<StudyPlanResponse>> getAllPlans(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(studyPlanService.getAllPlans(user));
    }

    @GetMapping("/{planId}")
    public ResponseEntity<StudyPlanResponse> getPlan(
            @PathVariable Long planId,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(studyPlanService.getPlan(planId, user));
    }

    @PatchMapping("/{planId}/days/{dayId}")
    public ResponseEntity<StudyPlanResponse> updatePlanDay(
            @PathVariable Long planId,
            @PathVariable Long dayId,
            @RequestBody Map<String, Object> updates,
            @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(studyPlanService.updatePlanDay(
            planId, dayId,
            (String) updates.get("notes"),
            updates.get("hoursCompleted") != null ? ((Number) updates.get("hoursCompleted")).floatValue() : null,
            updates.get("isCompleted") != null ? (Boolean) updates.get("isCompleted") : null,
            user));
    }
}
