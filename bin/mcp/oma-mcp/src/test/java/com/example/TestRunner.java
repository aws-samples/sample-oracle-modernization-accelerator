import com.example.OmaMcpTools;
import java.util.Map;

public class TestRunner {
    
    public static void main(String[] args) {
        OmaMcpTools tools = new OmaMcpTools();
        
        if (args.length == 0) {
            System.out.println("Usage:");
            System.out.println("  java TestRunner analyze <s3-path>");
            System.out.println("  java TestRunner report <s3-path> [objectType] [schemaName] [objectName]");
            System.out.println("  java TestRunner cleanup <s3-path>");
            System.out.println("\nExamples:");
            System.out.println("  java TestRunner analyze s3://bucket/prefix/");
            System.out.println("  java TestRunner report s3://bucket/prefix/");
            System.out.println("  java TestRunner report s3://bucket/prefix/ table");
            System.out.println("  java TestRunner report s3://bucket/prefix/ table DEMO");
            System.out.println("  java TestRunner report s3://bucket/prefix/ table DEMO ORDERS");
            System.out.println("  java TestRunner cleanup s3://bucket/prefix/");
            return;
        }
        
        String command = args[0];
        
        switch (command) {
            case "analyze" -> {
                if (args.length < 2) {
                    System.err.println("Error: S3 path required");
                    return;
                }
                String s3Path = args[1];
                System.out.println("Analyzing: " + s3Path);
                Map<String, Object> result = tools.analyzeDmsScProject(s3Path);
                printResult(result);
            }
            case "report" -> {
                if (args.length < 2) {
                    System.err.println("Error: S3 path required");
                    return;
                }
                String s3Path = args[1];
                String objectType = args.length > 2 ? args[2] : null;
                String schemaName = args.length > 3 ? args[3] : null;
                String objectName = args.length > 4 ? args[4] : null;
                
                System.out.print("Getting report for: " + s3Path);
                if (objectType != null) System.out.print(" [type=" + objectType + "]");
                if (schemaName != null) System.out.print(" [schema=" + schemaName + "]");
                if (objectName != null) System.out.print(" [name=" + objectName + "]");
                System.out.println();
                
                Map<String, Object> result = tools.reportDmsScProject(s3Path, objectType, schemaName, objectName);
                printResult(result);
            }
            case "cleanup" -> {
                String s3Path = args.length > 1 ? args[1] : "";
                System.out.println("Cleaning up: " + (s3Path.isEmpty() ? "all cache" : s3Path));
                Map<String, Object> result = tools.cleanupLocalCache(s3Path);
                printResult(result);
            }
            default -> System.err.println("Unknown command: " + command);
        }
    }
    
    private static void printResult(Map<String, Object> result) {
        System.out.println("\n=== Result ===");
        result.forEach((key, value) -> {
            if (value instanceof java.util.List) {
                System.out.println(key + ": " + ((java.util.List)value).size() + " items");
                System.out.println(value);
            } else {
                System.out.println(key + ": " + value);
            }
        });
    }
}
