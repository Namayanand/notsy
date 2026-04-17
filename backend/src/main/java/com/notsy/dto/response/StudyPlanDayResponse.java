package com.notsy.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyPlanDayResponse {
    private Long id;
    private Integer dayNumber;
    private LocalDate date;
    private String focus;
    private List<String> topics;
    private Float hoursPlanned;
    private Float hoursCompleted;
    private Boolean isCompleted;
    private String notes;
}