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
import com.finboost.bank.statement.parser.service.document.extraction.IBankSpecificParsingService;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentExtractionServiceImpl;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentIntelligenceProcessor;
import com.finboost.bank.statement.parser.service.document.extraction.azure.AzureDocumentIntelligenceResponseMapper;
import com.finboost.bank.statement.parser.service.document.extraction.bankstatement.BankStatementProcessorImpl;
import com.finboost.bank.statement.parser.service.document.extraction.post.processor.AnalyzeDocuments;
import com.finboost.bank.statement.parser.service.document.extraction.post.processor.EPdfCharacterExtractionService;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.HashMap;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class NativeTableMigrationTest {
    private static final File FIXTURES = new File("src/test/resources/pdf-samples-latest");

    private static Object processingConfig(String handlerSimpleName, String fixture) throws Exception {
        Class<?> handlerClass = Class.forName(
                "com.finboost.bank.statement.parser.service.bankstatement.bank." + handlerSimpleName);
        Object handler = handlerClass.getConstructor().newInstance();
        BankStatementVO statement = new BankStatementVO();
        statement.setDecryptedFile(new File(FIXTURES, fixture));
        return handlerClass.getMethod("getTableExtractorConfig", BankStatementVO.class)
                .invoke(handler, statement);
    }

    private static Object tableConfig(Object processingConfig) throws Exception {
        return processingConfig.getClass().getMethod("getTableExtractorConfig")
                .invoke(processingConfig);
    }

    private static String strategy(Object processingConfig) throws Exception {
        Object tableConfig = tableConfig(processingConfig);
        return String.valueOf(tableConfig.getClass().getMethod("getExtractionStrategy")
                .invoke(tableConfig));
    }

    private static DocumentExtractionResult extract(String handler, String fixture) throws Exception {
        Object processingConfig = processingConfig(handler, fixture);
        Object tableConfig = tableConfig(processingConfig);
        Class<?> extractorClass = Class.forName(
                "com.finboost.bank.statement.parser.tableextractor.PDFTableExtractor");
        Method extract = extractorClass.getMethod(
                "extractTables", File.class, String.class, tableConfig.getClass());
        return (DocumentExtractionResult) extract.invoke(
                null, new File(FIXTURES, fixture), null, tableConfig);
    }

    private static long cellCount(DocumentExtractionResult result) {
        assertNotNull(result);
        assertNotNull(result.getPages());
        return result.getPages().values().stream()
                .filter(page -> page != null && page.getTables() != null)
                .flatMap(page -> page.getTables().values().stream())
                .filter(table -> table != null && table.getCells() != null)
                .flatMap(table -> table.getCells().values().stream())
                .mapToLong(row -> row == null ? 0 : row.size())
                .sum();
    }

    private static void setProcessingConfig(DocumentExtractionRequest request, Object config)
            throws Exception {
        request.getClass()
                .getMethod("setBankStatementProcessingConfig", config.getClass())
                .invoke(request, config);
    }

    private static AzureDocumentExtractionServiceImpl configuredService(
            AzureDocumentIntelligenceProcessor remote,
            AzureDocumentIntelligenceResponseMapper mapper,
            AnalyzeDocuments analyzer) {
        AzureDocumentExtractionServiceImpl service = new AzureDocumentExtractionServiceImpl();
        service.setAzureDocumentIntelligenceProcessor(remote);
        service.setAzureDocumentIntelligenceResponseMapper(mapper);
        service.setAnalyzeDocuments(analyzer);
        service.setEPdfCharacterExtractionService(mock(EPdfCharacterExtractionService.class));
        service.setBankSpecificParsingService(mock(IBankSpecificParsingService.class));
        return service;
    }

    @Test
    void nativeStrategiesProduceStructuredRows() throws Exception {
        DocumentExtractionResult grid = extract("IciciHandler", "ICICI/format1.pdf");
        DocumentExtractionResult box = extract("BobHandler", "BOB/format1.pdf");
        DocumentExtractionResult selected = extract("BobHandler", "BOB/format18.pdf");

        assertAll(
                () -> assertEquals(2920, cellCount(grid), "grid-bordered extraction drifted"),
                () -> assertEquals(3174, cellCount(box), "box-guided extraction drifted"),
                () -> assertEquals(1200, cellCount(selected), "text-aligned row extraction drifted")
        );
    }

    @Test
    void supportedBankFormatsUseCorrectPolicy() throws Exception {
        List<String[]> formats = List.of(
                new String[]{"BobHandler", "BOB/format1.pdf", "BOX_LINE_TEXT_POSITION"},
                new String[]{"BobHandler", "BOB/format18.pdf", "SELECTED_ROWS_TEXT_POSITION"},
                new String[]{"HdfcHandler", "HDFC/format18.pdf", "GRID_LINE"},
                new String[]{"IciciHandler", "ICICI/format22.pdf", "BOX_LINE_TEXT_POSITION"},
                new String[]{"IdfcHandler", "IDFC/format1.pdf", "GRID_LINE"},
                new String[]{"IndianBankHandler", "INDIAN/format1.pdf", "GRID_LINE"},
                new String[]{"KotakHandler", "KOTAK/format2.pdf", "SELECTED_ROWS_TEXT_POSITION"},
                new String[]{"PunjabBankHandler", "PNB/format1.pdf", "GRID_LINE"},
                new String[]{"SbiHandler", "SBI/format1.pdf", "GRID_LINE"}
        );
        for (String[] format : formats) {
            assertEquals(format[2], strategy(processingConfig(format[0], format[1])),
                    format[1] + " selected the wrong extraction policy");
        }
    }

    @Test
    void nativeSuccessSkipsRemoteExtractor() throws Exception {
        AzureDocumentIntelligenceProcessor remote = mock(AzureDocumentIntelligenceProcessor.class);
        AzureDocumentIntelligenceResponseMapper mapper = mock(AzureDocumentIntelligenceResponseMapper.class);
        AnalyzeDocuments analyzer = mock(AnalyzeDocuments.class);
        when(analyzer.preProcessForVerificationByHeader(any(), eq(5))).thenReturn(null);
        when(analyzer.preProcessForVerification(any(), anyInt())).thenReturn(null);
        AzureDocumentExtractionServiceImpl service = configuredService(remote, mapper, analyzer);

        for (String[] format : List.of(
                new String[]{"IciciHandler", "ICICI/format1.pdf"},
                new String[]{"BobHandler", "BOB/format18.pdf"})) {
            Object config = processingConfig(format[0], format[1]);
            DocumentExtractionRequest request = new DocumentExtractionRequest();
            request.setStatementFile(new File(FIXTURES, format[1]));
            setProcessingConfig(request, config);
            assertNotNull(service.extractDocument(request));
        }

        verify(remote, never()).processDocument(any());
        verify(mapper, never()).mapAnalyzeResultToDocument(any());
    }

    @Test
    void unsupportedFormatsRetainRemoteFallback() throws Exception {
        Class<?> configClass = Class.forName(
                "com.finboost.bank.statement.parser.service.bankstatement.config.BankStatementProcessingConfig");
        Object defaultConfig = configClass.getConstructor().newInstance();
        Object tableConfig = tableConfig(defaultConfig);
        assertEquals("ML_BASED", String.valueOf(tableConfig.getClass()
                .getMethod("getExtractionStrategy").invoke(tableConfig)));

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

        AzureDocumentExtractionServiceImpl service = configuredService(remote, mapper, analyzer);
        DocumentExtractionRequest request = new DocumentExtractionRequest();
        request.setStatementFile(new File(FIXTURES, "YES/format1.pdf"));
        setProcessingConfig(request, defaultConfig);
        assertSame(mapped, service.extractDocument(request));
        verify(remote).processDocument(request.getStatementFile());
        verify(mapper).mapAnalyzeResultToDocument(remoteResult);
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

        for (String status : List.of(
                "NATIVE_PARSING",
                "ML_PARSING",
                "NATIVE_PARSING_FAILED_TO_ML_PARSING")) {
            statement.getClass().getMethod("setTableExtractorStatus", String.class)
                    .invoke(statement, status);
            RequestDocumentLogEntity documentLog = new RequestDocumentLogEntity(
                    statement, "BANK_ACCOUNT", "UPLOAD_STATEMENT", "SUCCESS");
            assertEquals(status, documentLog.getClass()
                    .getMethod("getTableExtractorStatus").invoke(documentLog));

            account.getClass().getMethod("setTableExtractorStatus", String.class)
                    .invoke(account, status);
            assertEquals(status, account.getClass()
                    .getMethod("getTableExtractorStatus").invoke(account));
            RequestAccountLogEntity accountLog = new RequestAccountLogEntity(
                    account, "BANK_ACCOUNT", "UPLOAD_STATEMENT", "SUCCESS");
            assertEquals(status, accountLog.getClass()
                    .getMethod("getTableExtractorStatus").invoke(accountLog));
        }
    }

    @Test
    void legacyDateParsingRemainsStable() throws Exception {
        SimpleDateFormat expected = new SimpleDateFormat("dd/MM/yyyy");
        assertEquals("28/04/2025", expected.format(
                BankStatementProcessorImpl.parseDate("28Apr2025(28Apr2025)")));
        assertNull(BankStatementProcessorImpl.parseDate("   "));
    }
}
