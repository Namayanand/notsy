package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyPlanResponse {

    private Long id;
    private String title;
    private String goalDescription;
    private LocalDate examDate;
    private Integer daysAvailable;
    private List<StudyPlanDayResponse> days;
    private Boolean isCompleted;
    private LocalDateTime createdAt;
}
