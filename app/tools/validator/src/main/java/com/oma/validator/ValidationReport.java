package com.oma.validator;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Validation report tracking test results
 */
public class ValidationReport {

    @JsonProperty("summary")
    private final Summary summary = new Summary();

    @JsonProperty("passed")
    private final List<TestResult> passed = Collections.synchronizedList(new ArrayList<>());

    @JsonProperty("failed")
    private final List<FailureResult> failed = Collections.synchronizedList(new ArrayList<>());

    @JsonProperty("errors")
    private final List<ErrorResult> errors = Collections.synchronizedList(new ArrayList<>());

    @JsonProperty("skipped")
    private final List<SkippedResult> skipped = Collections.synchronizedList(new ArrayList<>());

    /**
     * Add a passed test
     */
    public void addPassed(String sqlId, int retryCount) {
        summary.passed.incrementAndGet();
        if (retryCount > 0) {
            summary.retried.incrementAndGet();
        }
        passed.add(new TestResult(sqlId, retryCount));
    }

    /**
     * Add a failed test
     */
    public void addFailed(String sqlId, int retryCount, String oracleResult, String postgresResult) {
        summary.failed.incrementAndGet();
        if (retryCount > 0) {
            summary.retried.incrementAndGet();
        }
        failed.add(new FailureResult(sqlId, retryCount, oracleResult, postgresResult));
    }

    /**
     * Add a skipped test
     */
    public void addSkipped(String sqlId, String reason) {
        summary.skipped.incrementAndGet();
        skipped.add(new SkippedResult(sqlId, reason));
    }

    /**
     * Add an error
     */
    public void addError(String sqlId, String errorMessage) {
        summary.errors.incrementAndGet();
        errors.add(new ErrorResult(sqlId, errorMessage));
    }

    /**
     * Print summary to console
     */
    public void printSummary() {
        System.out.println("\n=== Validation Summary ===");
        System.out.println("Total:   " + summary.getTotal());
        System.out.println("Passed:  " + summary.passed.get() + " (" + getPercentage(summary.passed.get(), summary.getTotal()) + "%)");
        System.out.println("Failed:  " + summary.failed.get() + " (" + getPercentage(summary.failed.get(), summary.getTotal()) + "%)");
        System.out.println("Errors:  " + summary.errors.get() + " (" + getPercentage(summary.errors.get(), summary.getTotal()) + "%)");
        System.out.println("Skipped: " + summary.skipped.get() + " (" + getPercentage(summary.skipped.get(), summary.getTotal()) + "%)");
        System.out.println("Retried: " + summary.retried.get());

        if (!failed.isEmpty()) {
            System.out.println("\n=== Failed Tests ===");
            for (FailureResult failure : failed) {
                System.out.println("- " + failure.sqlId + " (retries: " + failure.retryCount + ")");
            }
        }

        if (!errors.isEmpty()) {
            System.out.println("\n=== Errors ===");
            for (ErrorResult error : errors) {
                System.out.println("- " + error.sqlId + ": " + error.errorMessage);
            }
        }
    }

    /**
     * Check if validation has failures
     */
    public boolean hasFailed() {
        return summary.failed.get() > 0 || summary.errors.get() > 0;
    }

    private double getPercentage(int value, int total) {
        if (total == 0) return 0.0;
        return Math.round((value * 100.0 / total) * 100.0) / 100.0;
    }

    // Inner classes for structured results

    public static class Summary {
        @JsonProperty("total")
        public int getTotal() {
            return passed.get() + failed.get() + errors.get() + skipped.get();
        }

        @JsonProperty("passed")
        private AtomicInteger passed = new AtomicInteger(0);

        @JsonProperty("failed")
        private AtomicInteger failed = new AtomicInteger(0);

        @JsonProperty("errors")
        private AtomicInteger errors = new AtomicInteger(0);

        @JsonProperty("skipped")
        private AtomicInteger skipped = new AtomicInteger(0);

        @JsonProperty("retried")
        private AtomicInteger retried = new AtomicInteger(0);
    }

    public static class TestResult {
        @JsonProperty("sql_id")
        public final String sqlId;

        @JsonProperty("retry_count")
        public final int retryCount;

        @JsonProperty("timestamp")
        public final String timestamp;

        public TestResult(String sqlId, int retryCount) {
            this.sqlId = sqlId;
            this.retryCount = retryCount;
            this.timestamp = new Date().toString();
        }
    }

    public static class FailureResult extends TestResult {
        @JsonProperty("oracle_result")
        public final String oracleResult;

        @JsonProperty("postgres_result")
        public final String postgresResult;

        public FailureResult(String sqlId, int retryCount, String oracleResult, String postgresResult) {
            super(sqlId, retryCount);
            this.oracleResult = oracleResult;
            this.postgresResult = postgresResult;
        }
    }

    public static class ErrorResult {
        @JsonProperty("sql_id")
        public final String sqlId;

        @JsonProperty("error_message")
        public final String errorMessage;

        @JsonProperty("timestamp")
        public final String timestamp;

        public ErrorResult(String sqlId, String errorMessage) {
            this.sqlId = sqlId;
            this.errorMessage = errorMessage;
            this.timestamp = new Date().toString();
        }
    }

    public static class SkippedResult {
        @JsonProperty("sql_id")
        public final String sqlId;

        @JsonProperty("reason")
        public final String reason;

        @JsonProperty("timestamp")
        public final String timestamp;

        public SkippedResult(String sqlId, String reason) {
            this.sqlId = sqlId;
            this.reason = reason;
            this.timestamp = new Date().toString();
        }
    }
}
