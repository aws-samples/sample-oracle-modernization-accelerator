import com.example.MmaScMcpTools;
import java.lang.reflect.Method;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;

public class TestLocalRunner {
    
    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.out.println("Usage: java TestLocalRunner <local-path>");
            System.out.println("Example: java TestLocalRunner ~/.mma-sc/mma-dms-sc-111709976242/dms-sc-migration-project");
            return;
        }
        
        String localPath = args[0].replace("~", System.getProperty("user.home"));
        Path basePath = Paths.get(localPath);
        
        System.out.println("Analyzing local files at: " + basePath);
        
        MmaScMcpTools tools = new MmaScMcpTools();
        
        // Use reflection to call private performAnalysis method
        Method method = MmaScMcpTools.class.getDeclaredMethod("performAnalysis", Path.class, String.class);
        method.setAccessible(true);
        
        String projectId = UUID.randomUUID().toString();
        Map<String, Object> result = (Map<String, Object>) method.invoke(tools, basePath, projectId);
        
        System.out.println("\n=== Analysis Result ===");
        System.out.println("project_id: " + projectId);
        System.out.println("local_base: " + basePath);
        result.forEach((key, value) -> {
            if (value instanceof java.util.List) {
                System.out.println(key + ": " + ((java.util.List)value).size() + " items");
            } else {
                System.out.println(key + ": " + value);
            }
        });
        
        System.out.println("\n=== DDL Files ===");
        Path ddlSource = basePath.resolve("ddl/source");
        Path ddlTarget = basePath.resolve("ddl/target");
        
        if (java.nio.file.Files.exists(ddlSource)) {
            long sourceCount = java.nio.file.Files.list(ddlSource).count();
            System.out.println("Source DDLs: " + sourceCount + " files in " + ddlSource);
        }
        
        if (java.nio.file.Files.exists(ddlTarget)) {
            long targetCount = java.nio.file.Files.list(ddlTarget).count();
            System.out.println("Target DDLs: " + targetCount + " files in " + ddlTarget);
        }
    }
}
