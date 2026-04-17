package com.notsy.dto.request;

import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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
public class CreateStudyPlanRequest {

    @NotBlank(message = "Title is required")
    private String title;

    private String goalDescription;

    @NotNull(message = "Exam date is required")
    @Future(message = "Exam date must be in the future")
    private LocalDate examDate;

    @NotNull(message = "Days available is required")
    @Min(value = 1, message = "At least 1 day is required")
    private Integer daysAvailable;

    private List<Long> topicIds; // topics to cover

    private Float hoursPerDay;

    private String difficultyPreference; // easy, balanced, hard
}
