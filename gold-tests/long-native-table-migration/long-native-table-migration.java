package com.finboost.bank.statement.parser.longhorizon;

import com.azure.ai.documentintelligence.models.AnalyzeResult;
import com.finboost.bank.statement.parser.datastore.log.entity.RequestAccountLogEntity;
import com.finboost.bank.statement.parser.datastore.log.entity.RequestDocumentLogEntity;
import com.finboost.bank.statement.parser.representation.bankAccount.AccountVO;
import com.finboost.bank.statement.parser.representation.bankAccount.BankAccountDetailsVO;
import com.finboost.bank.statement.parser.representation.bankstatement.AccountType;
import com.finboost.bank.statement.parser.representation.bankstatement.BankStatementVO;
import com.finboost.bank.statement.parser.representation.document.extraction.DocumentExtractionRequest;
import com.finboost.bank.statement.parser.representation.document.extraction.DocumentExtractionResult;
import com.finboost.bank.statement.parser.service.document.extraction.DocumentExtractionService;
import com.finboost.bank.statement.parser.service.document.extraction.IBankSpecificParsingService;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentExtractionServiceImpl;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentIntelligenceProcessor;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentIntelligenceResponseMapper;
import com.finboost.bank.statement.parser.service.document.extraction.bankstatement.BankStatementProcessorImpl;
import com.finboost.bank.statement.parser.service.document.extraction.post.processor.AnalyzeDocuments;
import com.finboost.bank.statement.parser.service.document.extraction.post.processor.EPdfCharacterExtractionService;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class NativeTableMigrationTest {
    private static final File FIXTURES = new File("src/test/resources/pdf-samples-latest");
    private static final Map<String, List<Object>> CONFIG_CACHE = new HashMap<>();
    private static final Map<String, DocumentExtractionResult> EXTRACTION_CACHE = new HashMap<>();
    private static List<Class<?>> applicationClasses;

    private static List<Class<?>> applicationClasses() throws Exception {
        if (applicationClasses != null) {
            return applicationClasses;
        }
        Path root = Paths.get("target/classes");
        List<Class<?>> found = new ArrayList<>();
        try (var paths = Files.walk(root)) {
            paths.filter(path -> path.toString().endsWith(".class"))
                    .filter(path -> !path.getFileName().toString().contains("$"))
                    .forEach(path -> {
                        String relative = root.relativize(path).toString();
                        String className = relative.substring(0, relative.length() - 6)
                                .replace(File.separatorChar, '.');
                        if (!className.startsWith("com.finboost.bank.statement.parser.")) {
                            return;
                        }
                        try {
                            found.add(Class.forName(className, false,
                                    NativeTableMigrationTest.class.getClassLoader()));
                        } catch (Throwable ignored) {
                            // Optional application classes may have unavailable runtime-only links.
                        }
                    });
        }
        applicationClasses = found;
        return found;
    }

    private static String bankName(String fixture) {
        String prefix = fixture.substring(0, fixture.indexOf('/'));
        return switch (prefix) {
            case "BOB" -> "BANK_OF_BARODA";
            case "INDIAN" -> "INDIAN_BANK";
            default -> prefix;
        };
    }

    private static List<String> bankAliases(String fixture) {
        String prefix = fixture.substring(0, fixture.indexOf('/')).toLowerCase(Locale.ROOT);
        return switch (prefix) {
            case "bob" -> List.of("bob", "baroda");
            case "indian" -> List.of("indian");
            case "pnb" -> List.of("pnb", "punjab");
            default -> List.of(prefix);
        };
    }

    private static int policyClassRank(Class<?> type, String fixture) {
        String name = type.getSimpleName().toLowerCase(Locale.ROOT);
        if (bankAliases(fixture).stream().anyMatch(name::contains)) {
            return 0;
        }
        if (name.contains("policy") || name.contains("resolver") || name.contains("handler")) {
            return 1;
        }
        return 2;
    }

    private static Object construct(Class<?> type) {
        if (type.isInterface() || Modifier.isAbstract(type.getModifiers())) {
            return null;
        }
        try {
            Constructor<?> constructor = type.getDeclaredConstructor();
            constructor.setAccessible(true);
            return constructor.newInstance();
        } catch (Throwable ignored) {
            return null;
        }
    }

    private static boolean policyMethod(Method method) {
        if (!Modifier.isPublic(method.getModifiers()) || method.getParameterCount() != 1) {
            return false;
        }
        if (!method.getParameterTypes()[0].isAssignableFrom(BankStatementVO.class)
                || method.getReturnType() == Void.TYPE) {
            return false;
        }
        String name = method.getName().toLowerCase(Locale.ROOT);
        return name.contains("config") || name.contains("policy")
                || name.contains("layout") || name.contains("extractor");
    }

    private static List<Object> configurationCandidates(String fixture) throws Exception {
        if (CONFIG_CACHE.containsKey(fixture)) {
            return CONFIG_CACHE.get(fixture);
        }
        BankStatementVO statement = new BankStatementVO();
        statement.setBank(bankName(fixture));
        statement.setDecryptedFile(new File(FIXTURES, fixture));

        List<Class<?>> ranked = new ArrayList<>(applicationClasses());
        ranked.sort(Comparator.comparingInt(type -> policyClassRank(type, fixture)));
        List<Object> configs = new ArrayList<>();
        for (Class<?> type : ranked) {
            if (policyClassRank(type, fixture) == 2) {
                continue;
            }
            Object target = null;
            for (Method method : type.getMethods()) {
                if (!policyMethod(method)) {
                    continue;
                }
                try {
                    if (!Modifier.isStatic(method.getModifiers()) && target == null) {
                        target = construct(type);
                    }
                    if (!Modifier.isStatic(method.getModifiers()) && target == null) {
                        continue;
                    }
                    Object value = method.invoke(
                            Modifier.isStatic(method.getModifiers()) ? null : target, statement);
                    if (value != null) {
                        configs.add(value);
                    }
                } catch (Throwable ignored) {
                    // A policy for another bank may legitimately reject this fixture.
                }
            }
        }
        CONFIG_CACHE.put(fixture, configs);
        return configs;
    }

    private static boolean simpleValue(Object value) {
        return value == null || value instanceof String || value instanceof Number
                || value instanceof Boolean || value.getClass().isEnum()
                || value instanceof File || value instanceof Class<?>;
    }

    private static List<Object> expandConfiguration(Object root) {
        List<Object> values = new ArrayList<>();
        Set<Object> seen = java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<>());
        expandConfiguration(root, values, seen, 0);
        return values;
    }

    private static void expandConfiguration(
            Object value, List<Object> values, Set<Object> seen, int depth) {
        if (value == null || simpleValue(value) || depth > 2 || !seen.add(value)) {
            return;
        }
        values.add(value);
        for (Method method : value.getClass().getMethods()) {
            if (!Modifier.isPublic(method.getModifiers()) || method.getParameterCount() != 0
                    || method.getDeclaringClass() == Object.class) {
                continue;
            }
            String name = method.getName().toLowerCase(Locale.ROOT);
            if (!(name.contains("config") || name.contains("policy")
                    || name.contains("layout") || name.contains("strategy"))) {
                continue;
            }
            try {
                expandConfiguration(method.invoke(value), values, seen, depth + 1);
            } catch (Throwable ignored) {
                // Optional nested policy data is not required to be readable.
            }
        }
    }

    private static List<Method> extractionMethods() throws Exception {
        List<Method> methods = new ArrayList<>();
        for (Class<?> type : applicationClasses()) {
            String className = type.getSimpleName().toLowerCase(Locale.ROOT);
            if (!(className.contains("extract") || className.contains("table")
                    || className.contains("pdf") || className.contains("native"))) {
                continue;
            }
            for (Method method : type.getMethods()) {
                String methodName = method.getName().toLowerCase(Locale.ROOT);
                if (Modifier.isPublic(method.getModifiers())
                        && DocumentExtractionResult.class.isAssignableFrom(method.getReturnType())
                        && (methodName.contains("extract") || methodName.contains("process")
                        || methodName.contains("read"))) {
                    methods.add(method);
                }
            }
        }
        return methods;
    }

    private static Object[] extractorArguments(Method method, File fixture, Object config) {
        Object[] arguments = new Object[method.getParameterCount()];
        boolean usedFile = false;
        boolean usedConfig = false;
        for (int index = 0; index < arguments.length; index++) {
            Class<?> parameter = method.getParameterTypes()[index];
            if (parameter.isAssignableFrom(File.class) && !usedFile) {
                arguments[index] = fixture;
                usedFile = true;
            } else if (parameter == String.class) {
                arguments[index] = null;
            } else if (config != null && parameter.isAssignableFrom(config.getClass())
                    && !usedConfig) {
                arguments[index] = config;
                usedConfig = true;
            } else {
                return null;
            }
        }
        return usedFile && (usedConfig || method.getParameterCount() == 1) ? arguments : null;
    }

    private static long cellCount(DocumentExtractionResult result) {
        if (result == null || result.getPages() == null) {
            return 0;
        }
        return result.getPages().values().stream()
                .filter(page -> page != null && page.getTables() != null)
                .flatMap(page -> page.getTables().values().stream())
                .filter(table -> table != null && table.getCells() != null)
                .flatMap(table -> table.getCells().values().stream())
                .mapToLong(row -> row == null ? 0 : row.size())
                .sum();
    }

    private static DocumentExtractionResult extractMatching(String fixture, long expectedCells)
            throws Exception {
        String cacheKey = fixture + "#" + expectedCells;
        if (EXTRACTION_CACHE.containsKey(cacheKey)) {
            return EXTRACTION_CACHE.get(cacheKey);
        }
        DocumentExtractionResult routed = nativeServiceResult(fixture, expectedCells);
        if (routed != null) {
            EXTRACTION_CACHE.put(cacheKey, routed);
            return routed;
        }
        File pdf = new File(FIXTURES, fixture);
        Set<Long> observed = new LinkedHashSet<>();
        List<Object> configs = new ArrayList<>();
        configs.add(null);
        for (Object outer : configurationCandidates(fixture)) {
            configs.addAll(expandConfiguration(outer));
        }
        for (Object config : configs) {
            for (Method method : extractionMethods()) {
                Object[] arguments = extractorArguments(method, pdf, config);
                if (arguments == null) {
                    continue;
                }
                Object target = Modifier.isStatic(method.getModifiers())
                        ? null : construct(method.getDeclaringClass());
                if (!Modifier.isStatic(method.getModifiers()) && target == null) {
                    continue;
                }
                try {
                    DocumentExtractionResult result = (DocumentExtractionResult)
                            method.invoke(target, arguments);
                    long count = cellCount(result);
                    observed.add(count);
                    if (count == expectedCells) {
                        EXTRACTION_CACHE.put(cacheKey, result);
                        return result;
                    }
                } catch (Throwable ignored) {
                    // Try the next compatible policy/extractor combination.
                }
            }
        }
        fail(fixture + " did not produce " + expectedCells
                + " structured cells; observed " + observed);
        return null;
    }

    private static void injectByType(Object target, Object dependency) throws Exception {
        for (Method method : target.getClass().getMethods()) {
            if (method.getName().startsWith("set") && method.getParameterCount() == 1
                    && method.getParameterTypes()[0].isInstance(dependency)) {
                method.invoke(target, dependency);
                return;
            }
        }
        for (Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            for (Field field : type.getDeclaredFields()) {
                if (!Modifier.isStatic(field.getModifiers())
                        && field.getType().isInstance(dependency)) {
                    field.setAccessible(true);
                    field.set(target, dependency);
                    return;
                }
            }
        }
        fail(target.getClass().getSimpleName() + " has no dependency slot for "
                + dependency.getClass().getSimpleName());
    }

    private static AzureDocumentExtractionServiceImpl configuredService(
            AzureDocumentIntelligenceProcessor remote,
            AzureDocumentIntelligenceResponseMapper mapper,
            AnalyzeDocuments analyzer) throws Exception {
        AzureDocumentExtractionServiceImpl service = new AzureDocumentExtractionServiceImpl();
        injectByType(service, remote);
        injectByType(service, mapper);
        injectByType(service, analyzer);
        injectByType(service, mock(EPdfCharacterExtractionService.class));
        injectByType(service, mock(IBankSpecificParsingService.class));
        return service;
    }

    private static boolean serviceCandidate(Class<?> type) {
        if (!DocumentExtractionService.class.isAssignableFrom(type)
                || type == AzureDocumentExtractionServiceImpl.class
                || type.isInterface() || Modifier.isAbstract(type.getModifiers())) {
            return false;
        }
        String name = type.getSimpleName().toLowerCase(Locale.ROOT);
        return name.contains("native") || name.contains("hybrid")
                || name.contains("routing") || name.contains("offline");
    }

    private static Object knownDependency(Class<?> required, List<Object> known) {
        if (required == Object.class) {
            return null;
        }
        for (Object candidate : known) {
            if (candidate != null && required.isInstance(candidate)) {
                return candidate;
            }
        }
        return null;
    }

    private static Class<?> genericElement(Type genericType) {
        if (!(genericType instanceof ParameterizedType parameterized)) {
            return null;
        }
        Type[] arguments = parameterized.getActualTypeArguments();
        return arguments.length == 1 && arguments[0] instanceof Class<?> type ? type : null;
    }

    private static Object dependencyFor(
            Class<?> required, Type genericType, List<Object> known,
            Set<Class<?>> constructing, int depth) throws Exception {
        Object dependency = knownDependency(required, known);
        if (dependency != null) {
            return dependency;
        }
        if (List.class.isAssignableFrom(required)) {
            Class<?> element = genericElement(genericType);
            if (element == null) {
                return null;
            }
            List<Object> implementations = new ArrayList<>();
            for (Class<?> type : applicationClasses()) {
                if (element.isAssignableFrom(type) && !type.isInterface()
                        && !Modifier.isAbstract(type.getModifiers())) {
                    Object value = construct(type);
                    if (value != null) {
                        wireObject(value, known, constructing, depth + 1);
                        implementations.add(value);
                    }
                }
            }
            return implementations;
        }
        if (depth > 7 || constructing.contains(required)) {
            return null;
        }
        List<Class<?>> candidates = new ArrayList<>();
        for (Class<?> type : applicationClasses()) {
            if (required.isAssignableFrom(type) && !type.isInterface()
                    && !Modifier.isAbstract(type.getModifiers())) {
                candidates.add(type);
            }
        }
        if (!required.isInterface() && !Modifier.isAbstract(required.getModifiers())) {
            candidates.add(0, required);
        }
        for (Class<?> type : candidates) {
            Object value = construct(type);
            if (value == null) {
                continue;
            }
            constructing.add(type);
            wireObject(value, known, constructing, depth + 1);
            constructing.remove(type);
            return value;
        }
        return null;
    }

    private static void wireObject(
            Object target, List<Object> known, Set<Class<?>> constructing, int depth)
            throws Exception {
        if (depth > 7) {
            return;
        }
        Set<Class<?>> assigned = new HashSet<>();
        for (Method method : target.getClass().getMethods()) {
            if (!method.getName().startsWith("set") || method.getParameterCount() != 1) {
                continue;
            }
            Class<?> required = method.getParameterTypes()[0];
            Object dependency = dependencyFor(
                    required, method.getGenericParameterTypes()[0], known, constructing, depth);
            if (dependency == null) {
                continue;
            }
            try {
                method.invoke(target, dependency);
                assigned.add(required);
            } catch (Throwable ignored) {
                // Try a field or another compatible implementation.
            }
        }
        for (Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            for (Field field : type.getDeclaredFields()) {
                if (Modifier.isStatic(field.getModifiers()) || Modifier.isFinal(field.getModifiers())
                        || assigned.stream().anyMatch(field.getType()::isAssignableFrom)) {
                    continue;
                }
                field.setAccessible(true);
                if (field.get(target) != null) {
                    continue;
                }
                Object dependency = dependencyFor(
                        field.getType(), field.getGenericType(), known, constructing, depth);
                if (dependency != null) {
                    field.set(target, dependency);
                }
            }
        }
    }

    private static List<DocumentExtractionService> configuredServices(
            AzureDocumentIntelligenceProcessor remote,
            AzureDocumentIntelligenceResponseMapper mapper,
            AnalyzeDocuments analyzer) throws Exception {
        AzureDocumentExtractionServiceImpl azure = configuredService(remote, mapper, analyzer);
        List<DocumentExtractionService> services = new ArrayList<>();
        List<Object> known = List.of(
                remote, mapper, analyzer,
                mock(EPdfCharacterExtractionService.class),
                mock(IBankSpecificParsingService.class), azure);
        for (Class<?> type : applicationClasses()) {
            if (!serviceCandidate(type)) {
                continue;
            }
            Object candidate = construct(type);
            if (candidate != null) {
                Set<Class<?>> constructing = new HashSet<>();
                constructing.add(type);
                wireObject(candidate, known, constructing, 0);
                services.add((DocumentExtractionService) candidate);
            }
        }
        services.add(azure);
        return services;
    }

    private static boolean attachConfiguration(DocumentExtractionRequest request, Object config) {
        for (Method method : request.getClass().getMethods()) {
            String name = method.getName().toLowerCase(Locale.ROOT);
            if (method.getParameterCount() == 1 && name.startsWith("set")
                    && (name.contains("config") || name.contains("policy") || name.contains("layout"))
                    && method.getParameterTypes()[0].isAssignableFrom(config.getClass())) {
                try {
                    method.invoke(request, config);
                    return true;
                } catch (Throwable ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    private static DocumentExtractionResult nativeServiceResult(
            String fixture, long expectedCells) throws Exception {
        List<Object> candidates = new ArrayList<>();
        candidates.add(null);
        for (Object outer : configurationCandidates(fixture)) {
            candidates.addAll(expandConfiguration(outer));
        }
        for (Object config : candidates) {
            AzureDocumentIntelligenceProcessor remote = mock(AzureDocumentIntelligenceProcessor.class);
            AzureDocumentIntelligenceResponseMapper mapper = mock(AzureDocumentIntelligenceResponseMapper.class);
            AnalyzeDocuments analyzer = mock(AnalyzeDocuments.class);
            when(analyzer.preProcessForVerificationByHeader(any(), eq(5))).thenReturn(null);
            when(analyzer.preProcessForVerification(any(), anyInt())).thenReturn(null);
            for (DocumentExtractionService service : configuredServices(remote, mapper, analyzer)) {
                DocumentExtractionRequest request = new DocumentExtractionRequest();
                request.setStatementFile(new File(FIXTURES, fixture));
                request.setBankName(bankName(fixture));
                if (config != null && !attachConfiguration(request, config)) {
                    continue;
                }
                try {
                    DocumentExtractionResult result = service.extractDocument(request);
                    long count = cellCount(result);
                    if (result != null && count > 0
                            && (expectedCells <= 0 || count == expectedCells)
                            && mockingDetails(remote).getInvocations().isEmpty()
                            && mockingDetails(mapper).getInvocations().isEmpty()) {
                        return result;
                    }
                } catch (Throwable ignored) {
                    // Try the next structurally compatible service/policy combination.
                }
            }
        }
        return null;
    }

    private static boolean nativeServicePath(String fixture) throws Exception {
        return nativeServiceResult(fixture, 0) != null;
    }

    private static boolean remoteFallbackPath(String fixture) throws Exception {
        String unknownBank = "UNSUPPORTED_TEST_BANK";
        List<Object> candidates = new ArrayList<>();
        candidates.add(null);
        for (Object outer : configurationCandidates(fixture)) {
            candidates.addAll(expandConfiguration(outer));
        }
        for (Object config : candidates) {
            AzureDocumentIntelligenceProcessor remote = mock(AzureDocumentIntelligenceProcessor.class);
            AzureDocumentIntelligenceResponseMapper mapper = mock(AzureDocumentIntelligenceResponseMapper.class);
            AnalyzeDocuments analyzer = mock(AnalyzeDocuments.class);
            AnalyzeResult remoteResult = mock(AnalyzeResult.class);
            DocumentExtractionResult mapped = new DocumentExtractionResult();
            mapped.setPages(new HashMap<>());
            mapped.setNoOfPages(0);
            when(remote.processDocument(any())).thenReturn(remoteResult);
            when(mapper.mapAnalyzeResultToDocument(remoteResult)).thenReturn(mapped);
            when(analyzer.preProcessForVerificationByHeader(any(), eq(5))).thenReturn(null);
            when(analyzer.preProcessForVerification(any(), anyInt())).thenReturn(null);
            for (DocumentExtractionService service : configuredServices(remote, mapper, analyzer)) {
                DocumentExtractionRequest request = new DocumentExtractionRequest();
                request.setStatementFile(new File(FIXTURES, fixture));
                request.setBankName(unknownBank);
                if (config != null && !attachConfiguration(request, config)) {
                    continue;
                }
                try {
                    DocumentExtractionResult result = service.extractDocument(request);
                    if (result == mapped
                            && !mockingDetails(remote).getInvocations().isEmpty()
                            && !mockingDetails(mapper).getInvocations().isEmpty()) {
                        return true;
                    }
                } catch (Throwable ignored) {
                    // An unsupported service/configuration shape is not the default route.
                }
            }
        }
        return false;
    }

    private static boolean statusHint(String methodName) {
        String name = methodName.toLowerCase(Locale.ROOT);
        return name.contains("extract") || name.contains("parsing")
                || name.contains("native") || name.contains("remote")
                || name.contains("fallback");
    }

    private static Method statusSetter(Class<?> type) {
        List<Method> candidates = new ArrayList<>();
        for (Method method : type.getMethods()) {
            if (method.getName().startsWith("set") && statusHint(method.getName())
                    && method.getParameterCount() == 1
                    && (method.getParameterTypes()[0] == String.class
                    || method.getParameterTypes()[0].isEnum())) {
                candidates.add(method);
            }
        }
        candidates.sort(Comparator.comparingInt(method ->
                method.getName().toLowerCase(Locale.ROOT).contains("status") ? 0 : 1));
        for (Method method : candidates) {
            if (method.getParameterTypes()[0] == String.class
                    || (semanticStatus(method, 0) != null
                    && semanticStatus(method, 1) != null
                    && semanticStatus(method, 2) != null)) {
                return method;
            }
        }
        return null;
    }

    private static Method statusGetter(Class<?> type, Method setter) {
        String property = setter == null ? null : setter.getName().substring(3);
        if (property != null) {
            for (String prefix : List.of("get", "is")) {
                try {
                    Method exact = type.getMethod(prefix + property);
                    if (exact.getParameterCount() == 0
                            && (exact.getReturnType() == String.class
                            || exact.getReturnType().isEnum())) {
                        return exact;
                    }
                } catch (NoSuchMethodException ignored) {
                    // Fall through to semantic discovery.
                }
            }
        }
        for (Method method : type.getMethods()) {
            if ((method.getName().startsWith("get") || method.getName().startsWith("is"))
                    && statusHint(method.getName()) && method.getParameterCount() == 0
                    && (method.getReturnType() == String.class || method.getReturnType().isEnum())) {
                return method;
            }
        }
        return null;
    }

    private static Object semanticStatus(Method setter, int semantic) {
        Class<?> type = setter.getParameterTypes()[0];
        if (type == String.class) {
            return switch (semantic) {
                case 0 -> "NATIVE_PARSING";
                case 1 -> "ML_PARSING";
                default -> "NATIVE_PARSING_FAILED_TO_ML_PARSING";
            };
        }
        Object[] constants = type.getEnumConstants();
        for (Object constant : constants) {
            String name = String.valueOf(constant).toUpperCase(Locale.ROOT);
            boolean fallback = name.contains("FALL") || name.contains("FAIL");
            if (semantic == 2 && fallback) {
                return constant;
            }
            if (semantic == 0 && name.contains("NATIVE") && !fallback) {
                return constant;
            }
            if (semantic == 1 && (name.contains("ML") || name.contains("REMOTE")) && !fallback) {
                return constant;
            }
        }
        return null;
    }

    private static String setAndReadStatus(Object bean, int semantic) throws Exception {
        Method setter = statusSetter(bean.getClass());
        Method getter = statusGetter(bean.getClass(), setter);
        assertNotNull(setter, bean.getClass().getSimpleName() + " has no extraction-status setter");
        assertNotNull(getter, bean.getClass().getSimpleName() + " has no extraction-status getter");
        Object value = semanticStatus(setter, semantic);
        assertNotNull(value, "status type does not represent native, ML, and fallback states");
        setter.invoke(bean, value);
        return String.valueOf(getter.invoke(bean));
    }

    private static String readStatus(Object bean, String expected) throws Exception {
        for (Method method : bean.getClass().getMethods()) {
            if ((method.getName().startsWith("get") || method.getName().startsWith("is"))
                    && statusHint(method.getName()) && method.getParameterCount() == 0
                    && (method.getReturnType() == String.class || method.getReturnType().isEnum())) {
                if (expected.equals(String.valueOf(method.invoke(bean)))) {
                    return expected;
                }
            }
        }
        fail(bean.getClass().getSimpleName() + " did not persist extraction status " + expected);
        return null;
    }

    @Test
    void nativeStrategiesProduceStructuredRows() throws Exception {
        assertAll(
                () -> assertEquals(2920, cellCount(
                        extractMatching("ICICI/format1.pdf", 2920))),
                () -> assertEquals(3174, cellCount(
                        extractMatching("BOB/format1.pdf", 3174))),
                () -> assertEquals(1200, cellCount(
                        extractMatching("BOB/format18.pdf", 1200)))
        );
    }

    @Test
    void supportedBankFormatsUseCorrectPolicy() throws Exception {
        Map<String, Long> fixtures = Map.of(
                "HDFC/format18.pdf", 350L,
                "ICICI/format22.pdf", 632L,
                "IDFC/format1.pdf", 350L,
                "INDIAN/format1.pdf", 1096L,
                "KOTAK/format2.pdf", 465L,
                "PNB/format1.pdf", 1224L,
                "SBI/format1.pdf", 1760L);
        for (Map.Entry<String, Long> fixture : fixtures.entrySet()) {
            assertEquals(fixture.getValue().longValue(),
                    cellCount(extractMatching(fixture.getKey(), fixture.getValue())),
                    fixture.getKey() + " selected the wrong native policy");
        }
    }

    @Test
    void nativeSuccessSkipsRemoteExtractor() throws Exception {
        assertAll(
                () -> assertTrue(nativeServicePath("ICICI/format1.pdf"),
                        "grid-native extraction did not bypass the remote client"),
                () -> assertTrue(nativeServicePath("BOB/format18.pdf"),
                        "row-selected native extraction did not bypass the remote client")
        );
    }

    @Test
    void unsupportedFormatsRetainRemoteFallback() throws Exception {
        assertTrue(remoteFallbackPath("YES/format1.pdf"),
                "an unknown bank family did not use the remote ML boundary");
    }

    @Test
    void usageStatusPropagatesToApiAndLogs() throws Exception {
        BankStatementVO statement = new BankStatementVO();
        statement.setBank("HDFC");
        statement.setAccountType(AccountType.SAVING);
        BankAccountDetailsVO details = new BankAccountDetailsVO();
        details.setBankCode("HDFC");
        details.setAccountType(AccountType.SAVING);
        AccountVO account = new AccountVO();
        account.setBankAccountDetails(details);

        Set<String> statementStates = new HashSet<>();
        Set<String> accountStates = new HashSet<>();
        for (int semantic = 0; semantic < 3; semantic++) {
            String statementStatus = setAndReadStatus(statement, semantic);
            statementStates.add(statementStatus);
            RequestDocumentLogEntity documentLog = new RequestDocumentLogEntity(
                    statement, "BANK_ACCOUNT", "UPLOAD_STATEMENT", "SUCCESS");
            assertEquals(statementStatus, readStatus(documentLog, statementStatus));

            String accountStatus = setAndReadStatus(account, semantic);
            accountStates.add(accountStatus);
            RequestAccountLogEntity accountLog = new RequestAccountLogEntity(
                    account, "BANK_ACCOUNT", "UPLOAD_STATEMENT", "SUCCESS");
            assertEquals(accountStatus, readStatus(accountLog, accountStatus));
        }
        assertEquals(3, statementStates.size(), "statement API collapsed extraction states");
        assertEquals(3, accountStates.size(), "account API collapsed extraction states");
    }

    @Test
    void legacyDateParsingRemainsStable() throws Exception {
        SimpleDateFormat expected = new SimpleDateFormat("dd/MM/yyyy");
        assertEquals("28/04/2025", expected.format(
                BankStatementProcessorImpl.parseDate("28Apr2025(28Apr2025)")));
        assertNull(BankStatementProcessorImpl.parseDate("   "));
    }
}
