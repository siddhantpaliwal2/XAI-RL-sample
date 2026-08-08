import { plainToInstance } from 'class-transformer';
import { validate } from 'class-validator';

const mockCreatePolicy = jest.fn();
const mockCreateRole = jest.fn();
const mockAttachRolePolicy = jest.fn();
const mockUpdateAssumeRolePolicy = jest.fn();
const mockS3Send = jest.fn();

jest.mock('@aws-sdk/client-iam', () => ({
    IAM: jest.fn(() => ({
        createPolicy: mockCreatePolicy,
        createRole: mockCreateRole,
        attachRolePolicy: mockAttachRolePolicy,
        updateAssumeRolePolicy: mockUpdateAssumeRolePolicy,
    })),
}));
jest.mock('@aws-sdk/client-s3', () => ({
    S3Client: jest.fn(() => ({ send: mockS3Send })),
    PutObjectCommand: jest.fn((input) => ({ input })),
}));

import { CreateMeasurementConfigDto, measurementMode } from './dto/create-measurement-config.dto';
import {
    DatastoreAccessInformation,
    MeasurementConfigEntity,
    SupportedDatastores,
} from './entities/measurement-config.entity';
import {
    DlqType,
    StandardMeasurementEntity,
} from './entities/standardMeasurement.entity';
import { MeasurementConfigService } from './measurement-config.service';
import { PrivateAPIUsageController } from '../usage/usage.controller';

describe('S3 datastore measurement configuration', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        process.env.DB_MEASUREMENT_BUCKET_NAME = 'usage-bucket';
        process.env.DB_MEASUREMENT_DLQ_BUCKET_NAME = 'usage-dlq';
        process.env.AWS_REGION = 'us-east-1';
        process.env.STAGE = 'test';
        mockCreatePolicy.mockResolvedValue({ Policy: { Arn: 'arn:aws:iam::paigo:policy/datastore' } });
        mockCreateRole.mockResolvedValue({ Role: { Arn: 'arn:aws:iam::paigo:role/datastore' } });
        mockAttachRolePolicy.mockResolvedValue({});
        mockUpdateAssumeRolePolicy.mockResolvedValue({});
        mockS3Send.mockResolvedValue({});
    });

    const input = (extra: Record<string, unknown> = {}) =>
        plainToInstance(CreateMeasurementConfigDto, {
            businessID: 'business-1',
            measurementName: 'S3 usage',
            measurementMode: measurementMode.datastoreBased,
            measurementConfiguration: {
                platform: SupportedDatastores.s3,
                accountId: '123456789012',
            },
            ...extra,
        });

    it('accepts datastoreBased S3 configuration and materializes nested validation', async () => {
        const value = input();
        await expect(validate(value)).resolves.toEqual([]);
        expect(value.measurementConfiguration).toBeInstanceOf(DatastoreAccessInformation);
    });

    it('defaults an omitted platform to S3 and region to us-east-1', () => {
        const access = new DatastoreAccessInformation({ accountId: '123456789012' } as any);
        expect(access.platform).toBe(SupportedDatastores.s3);
        expect(access.region).toBe('us-east-1');
    });

    it('persists and restores every datastore access field', () => {
        const point = { stringField: jest.fn(), tag: jest.fn() };
        const entity = new MeasurementConfigEntity({
            measurementId: 'measurement-1',
            measurementMode: measurementMode.datastoreBased,
            measurementConfiguration: {
                platform: SupportedDatastores.s3,
                accountId: '123456789012',
                ingestion: 's3://usage-bucket/business-1',
                dlq: 's3://usage-dlq/business-1',
                iamRoleArn: 'arn:role',
                externalId: 'external-1',
                region: 'us-west-2',
            },
            businessID: 'business-1',
            subject: 'subject-1',
            measurementName: 'S3 usage',
        } as any);
        MeasurementConfigEntity.transformer(entity, { getPoint: jest.fn(() => point) } as any);
        for (const [key, value] of [
            ['platform', 's3'],
            ['accountId', '123456789012'],
            ['ingestion', 's3://usage-bucket/business-1'],
            ['dlq', 's3://usage-dlq/business-1'],
            ['iamRoleArn', 'arn:role'],
            ['externalId', 'external-1'],
            ['region', 'us-west-2'],
        ]) {
            expect(point.tag).toHaveBeenCalledWith(key, value);
        }
        const restored = MeasurementConfigEntity.dbModelToEntity({
            _value: measurementMode.datastoreBased,
            measurementId: 'measurement-1',
            businessID: 'business-1',
            subject: 'subject-1',
            measurementName: 'S3 usage',
            platform: 's3',
            accountId: '123456789012',
            ingestion: 's3://usage-bucket/business-1',
            dlq: 's3://usage-dlq/business-1',
            iamRoleArn: 'arn:role',
            externalId: 'external-1',
            region: 'us-west-2',
        });
        expect(restored.measurementConfiguration).toEqual(
            expect.objectContaining({ accountId: '123456789012', externalId: 'external-1', region: 'us-west-2' }),
        );
    });

    it('provisions a scoped IAM role and returns ingestion and DLQ locations', async () => {
        const result = await DatastoreAccessInformation.setupAccess(
            new MeasurementConfigEntity({
                measurementId: 'measurement-1',
                measurementMode: measurementMode.datastoreBased,
                measurementConfiguration: { platform: 's3', accountId: '123456789012' },
                businessID: 'business-1',
                subject: 'subject-1',
                measurementName: 'S3 usage',
            } as any),
        );
        expect(result).toEqual(
            expect.objectContaining({
                iamRoleArn: 'arn:aws:iam::paigo:role/datastore',
                ingestion: 's3://usage-bucket/business-1',
                dlq: 's3://usage-dlq/business-1',
                region: 'us-east-1',
            }),
        );
        expect(result.externalId).toEqual(expect.any(String));
        expect(result.externalId).not.toHaveLength(0);
        const role = mockCreateRole.mock.calls[0][0];
        expect(role.RoleName).toBe('datastore-business-1-measurement-1');
        expect(JSON.parse(role.AssumeRolePolicyDocument).Statement[0]).toEqual(
            expect.objectContaining({
                Principal: { AWS: 'arn:aws:iam::123456789012:root' },
                Condition: { StringEquals: { 'sts:ExternalId': result.externalId } },
            }),
        );
        expect(mockAttachRolePolicy).toHaveBeenCalledWith({
            PolicyArn: 'arn:aws:iam::paigo:policy/datastore',
            RoleName: 'datastore-business-1-measurement-1',
        });
    });

    it('updates account trust while preserving the existing role and external ID', async () => {
        const result = await DatastoreAccessInformation.updateAccess(
            new MeasurementConfigEntity({
                measurementId: 'measurement-1',
                measurementMode: measurementMode.datastoreBased,
                measurementConfiguration: {
                    platform: 's3',
                    accountId: '999999999999',
                    iamRoleArn: 'arn:role',
                    externalId: 'external-1',
                },
                businessID: 'business-1',
                subject: 'subject-1',
                measurementName: 'S3 usage',
            } as any),
        );
        expect(result).toEqual(expect.objectContaining({ iamRoleArn: 'arn:role', externalId: 'external-1' }));
        const policy = JSON.parse(mockUpdateAssumeRolePolicy.mock.calls[0][0].PolicyDocument);
        expect(policy.Statement[0].Principal.AWS).toBe('arn:aws:iam::999999999999:root');
        expect(policy.Statement[0].Condition.StringEquals['sts:ExternalId']).toBe('external-1');
    });

    it('creates, persists, and returns provisioned datastore configuration', async () => {
        const point = { stringField: jest.fn(), tag: jest.fn() };
        const loadPoints = jest.fn();
        const service = new MeasurementConfigService(
            { getPoint: jest.fn(() => point), loadPoints } as any,
            {} as any,
        );
        const result = await service.create(input(), 'subject-1');
        expect(result).toEqual(
            expect.objectContaining({
                measurementId: expect.any(String),
                iamRoleArn: 'arn:aws:iam::paigo:role/datastore',
                ingestion: 's3://usage-bucket/business-1',
                dlq: 's3://usage-dlq/business-1',
            }),
        );
        expect(loadPoints).toHaveBeenCalledTimes(1);
    });
});

describe('S3 connector usage delivery', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        process.env.DB_MEASUREMENT_DLQ_BUCKET_NAME = 'usage-dlq';
        mockS3Send.mockResolvedValue({});
    });

    it('derives the business from the object key and ingests a valid record', async () => {
        const create = jest.fn(async () => ({ message: 'created' }));
        const controller = new PrivateAPIUsageController({ create } as any);
        await expect(
            controller.dbUsage({
                s3Key: 'business-1/2023/usage.ndjson',
                message: JSON.stringify({ dimensionId: 'dimension-1', recordValue: '4', metadata: { source: 's3' } }),
            }),
        ).resolves.toEqual({ message: 'created' });
        expect(create).toHaveBeenCalledWith(
            expect.objectContaining({ businessID: 'business-1', dimensionId: 'dimension-1', recordValue: '4' }),
        );
    });

    it('writes malformed connector records to the mirrored message key in the DLQ', async () => {
        const controller = new PrivateAPIUsageController({ create: jest.fn() } as any);
        await controller.dbUsage({ s3Key: 'business-1/customer/usage.ndjson', message: '{not-json' });
        expect(mockS3Send).toHaveBeenCalledTimes(1);
        const command = mockS3Send.mock.calls[0][0];
        expect(command.input.Bucket).toBe('usage-dlq');
        expect(command.input.Key).toBe('business-1/customer/usage.ndjson.message.text');
        expect(JSON.parse(command.input.Body)).toEqual(
            expect.objectContaining({
                failedDocument: expect.objectContaining({ s3Key: 'business-1/customer/usage.ndjson' }),
                metadata: expect.objectContaining({ results: 'failed to load data' }),
            }),
        );
    });

    it('keeps the generic DLQ writer usable for an already-relative source key', async () => {
        await StandardMeasurementEntity.publishFailureToDLQ(
            { message: 'bad' },
            {
                id: 'failure-1',
                timestamp: '2023-02-24T00:00:00.000Z',
                message: 'invalid record',
                results: 'discarded',
                orginalProcessedName: 'customer/file.json',
            },
            DlqType.s3,
            'business-1',
        );
        expect(mockS3Send.mock.calls[0][0].input.Key).toBe('business-1/customer/file.json.message.text');
    });
});
