import { NotFoundException } from '@nestjs/common';

import { EmailinfraService } from './emailinfra.service';

// The contract intentionally does not require the historical implementation's
// enum or repository-wrapper names. Both an injected repository and a domain
// entity with static persistence methods are valid designs.
const emailAccountModule = require('./entities/emailAccount.entity') as any;
const EmailAccount = emailAccountModule.EmailAccount as any;
const EmailAccountRepository = emailAccountModule.EmailAccountEntity as any;

type StoredAccount = Record<string, any>;

function ranked(records: StoredAccount[]): StoredAccount[] {
  const domainCounts = records.reduce<Record<string, number>>((counts, record) => {
    const domain = record.domain ?? record.email?.split('@')[1] ?? '';
    counts[domain] = (counts[domain] ?? 0) + 1;
    return counts;
  }, {});
  return [...records].sort((a, b) => {
    const deliverability =
      (b.deliverabilityScore ?? -1) - (a.deliverabilityScore ?? -1);
    if (deliverability !== 0) return deliverability;
    const campaigns =
      (a.numberOfCampaignAssociated ?? a.campaignIds?.length ?? 0) -
      (b.numberOfCampaignAssociated ?? b.campaignIds?.length ?? 0);
    if (campaigns !== 0) return campaigns;
    const aDomain = a.domain ?? a.email?.split('@')[1] ?? '';
    const bDomain = b.domain ?? b.email?.split('@')[1] ?? '';
    const domains = (domainCounts[aDomain] ?? 1) - (domainCounts[bDomain] ?? 1);
    if (domains !== 0) return domains;
    return new Date(a.createdAt ?? 8640000000000000).getTime() -
      new Date(b.createdAt ?? 8640000000000000).getTime();
  });
}

function memoryDatastore(initial: StoredAccount[] = []): any {
  const records = new Map<string, StoredAccount>();
  for (const record of initial) {
    const id = `${record.smartleadInboxId ?? record.id}`;
    records.set(id, { ...record, id, smartleadInboxId: id });
  }

  const store = jest.fn(async (request: any) => {
    const data = { ...request.data };
    const id = `${request.context?.uniqueId ?? data.smartleadInboxId ?? data.id}`;
    records.set(id, { ...data, id, smartleadInboxId: id });
    return {};
  });
  const getById = jest.fn(async (request: any) => ({
    data: records.get(`${request.id}`),
  }));
  const getByField = jest.fn(async (request: any) => {
    let data = [...records.values()];
    if (request.fieldKey === 'id' && request.fieldValue?.$in) {
      const ids = new Set(request.fieldValue.$in.map(String));
      data = data.filter((record) => ids.has(`${record.id}`));
    } else if (request.fieldKey === 'data.email') {
      data = data.filter((record) => record.email === request.fieldValue);
    } else if (request.fieldKey === 'data.smartleadClientId') {
      data = data.filter(
        (record) => `${record.smartleadClientId}` === `${request.fieldValue}`,
      );
    } else if (request.fieldKey === 'data.smartleadInboxId') {
      data = data.filter((record) => Boolean(record.smartleadInboxId));
    }
    if (request.pagination) {
      const start = request.pagination.page * request.pagination.pageSize;
      data = data.slice(start, start + request.pagination.pageSize);
    }
    return { data };
  });
  const getManyAndAggregate = jest.fn(
    async (
      filter: Record<string, any>,
      _context: any,
      _pipeline: any[],
      pagination?: { page: number; pageSize: number },
    ) => {
      let data = [...records.values()];
      const clientId = filter?.['data.smartleadClientId'];
      if (clientId !== undefined) {
        data = data.filter(
          (record) => `${record.smartleadClientId}` === `${clientId}`,
        );
      }
      if (pagination) {
        const start = pagination.page * pagination.pageSize;
        data = data.slice(start, start + pagination.pageSize);
      }
      return data;
    },
  );
  const remove = jest.fn(async (request: any) => {
    records.delete(`${request.id}`);
  });

  return { store, getById, getByField, getManyAndAggregate, remove, records };
}

function subject(db: any): { service: any; repository?: any } {
  const repository = EmailAccountRepository
    ? new EmailAccountRepository(db)
    : undefined;
  return {
    repository,
    service: new (EmailinfraService as any)(repository ?? db),
  };
}

function clientLookup(service: any, smartleadClientId: string): Promise<any[]> {
  const method =
    service.getEmailAccountsBySmartleadClientId ??
    service.getEmailAccountBySmartleadClientId;
  return method.call(service, smartleadClientId);
}

describe('Email inbox infrastructure contract', () => {
  afterEach(() => jest.restoreAllMocks());

  it('derives stable identity, domain, counters, and deliverability bands', () => {
    const cases: Array<[number | undefined, string]> = [
      [100, 'High'],
      [99, 'Medium'],
      [98, 'Medium'],
      [97, 'Low'],
      [95, 'Low'],
      [94, 'Burned'],
      [undefined, 'Unknown'],
    ];
    for (const [score, expected] of cases) {
      const account = new EmailAccount({
        email: 'owner@example.com',
        smartleadInboxId: 'inbox-1',
        campaignIds: ['campaign-1'],
        deliverabilityScore: score,
      });
      expect(account.id).toBe('inbox-1');
      expect(account.domain).toBe('example.com');
      expect(account.numberOfCampaignAssociated).toBe(1);
      expect(account.deliverability).toBe(expected);
      expect(account.tags).toEqual([]);
    }
  });

  it('persists the normalized email account in the dedicated collection', async () => {
    const db = memoryDatastore();
    const account = new EmailAccount({
      email: 'owner@example.com',
      smartleadClientId: 'client-1',
      smartleadInboxId: 'inbox-1',
      deliverabilityScore: 100,
      createdAt: '2025-01-01T00:00:00.000Z',
    });

    await account.save(db);
    expect(db.store).toHaveBeenCalledTimes(1);
    const request = db.store.mock.calls[0][0];
    expect(request.context.uniqueId).toBe('inbox-1');
    expect(`${request.context.documentType}`).toBe('EMAIL_ACCOUNT');
    expect(request.data).toEqual(
      expect.objectContaining({
        id: 'inbox-1',
        domain: 'example.com',
        deliverability: 'High',
      }),
    );
  });

  it('looks up accounts through inbox-specific datastore fields', async () => {
    const db = memoryDatastore([
      {
        id: '1',
        email: 'a@example.com',
        smartleadClientId: 'client-1',
        smartleadInboxId: '1',
      },
      {
        id: '2',
        email: 'b@example.com',
        smartleadClientId: 'client-1',
        smartleadInboxId: '2',
      },
    ]);
    const { service } = subject(db);

    await expect(service.getEmailAccount('1')).resolves.toEqual(
      expect.objectContaining({ id: '1' }),
    );
    await expect(service.getEmailAccountByEmail('a@example.com')).resolves.toEqual(
      expect.objectContaining({ id: '1' }),
    );
    await expect(clientLookup(service, 'client-1')).resolves.toHaveLength(2);
    await expect(
      service.getAllEmailAccounts({ page: 0, pageSize: 1 }),
    ).resolves.toHaveLength(1);
  });

  it('rejects a lookup when no account has the requested email', async () => {
    const { service } = subject(memoryDatastore());
    await expect(
      service.getEmailAccountByEmail('missing@example.com'),
    ).rejects.toBeInstanceOf(NotFoundException);
  });

  it('deduplicates campaign associations and refuses partial id sets', async () => {
    const db = memoryDatastore([
      { id: '1', smartleadInboxId: '1', email: 'a@example.com', campaignIds: [] },
      { id: '2', smartleadInboxId: '2', email: 'b@example.com', campaignIds: [] },
    ]);
    const { service } = subject(db);
    await service.associateEmailAccountsWithCampaign({
      emailAccountIds: ['1', '1', '2'],
      campaignId: 'campaign-1',
    });
    expect(db.store).toHaveBeenCalledTimes(2);

    const partialDb = memoryDatastore([
      { id: '1', smartleadInboxId: '1', email: 'a@example.com', campaignIds: [] },
    ]);
    const partial = subject(partialDb).service;
    await expect(
      partial.associateEmailAccountsWithCampaign({
        emailAccountIds: ['1', 'missing'],
        campaignId: 'campaign-1',
      }),
    ).rejects.toBeInstanceOf(NotFoundException);
    expect(partialDb.store).not.toHaveBeenCalled();
  });

  it('skips existing campaign links and persists each new association once', async () => {
    const db = memoryDatastore([
      {
        id: '1', smartleadInboxId: '1', email: 'a@example.com',
        campaignIds: ['campaign-1'],
      },
      {
        id: '2', smartleadInboxId: '2', email: 'b@example.com', campaignIds: [],
      },
    ]);
    const { service } = subject(db);
    await service.associateEmailAccountsWithCampaign({
      emailAccountIds: ['1', '2'],
      campaignId: 'campaign-1',
    });

    expect(db.store).toHaveBeenCalledTimes(1);
    expect(db.store.mock.calls[0][0].data).toEqual(
      expect.objectContaining({
        id: '2',
        campaignIds: ['campaign-1'],
        numberOfCampaignAssociated: 1,
      }),
    );
  });

  const rankingFixture = () => [
    {
      id: 'busy', smartleadInboxId: 'busy', smartleadClientId: 'client-1',
      email: 'busy@example.com', deliverabilityScore: 99, campaignIds: ['1', '2'],
      numberOfCampaignAssociated: 2, createdAt: '2018-01-01T00:00:00.000Z',
    },
    {
      id: 'shared', smartleadInboxId: 'shared', smartleadClientId: 'client-1',
      email: 'first@shared.com', deliverabilityScore: 99, campaignIds: [],
      numberOfCampaignAssociated: 0, createdAt: '2018-01-01T00:00:00.000Z',
    },
    {
      id: 'new', smartleadInboxId: 'new', smartleadClientId: 'client-1',
      email: 'new@solo.com', deliverabilityScore: 99, campaignIds: [],
      numberOfCampaignAssociated: 0, createdAt: '2022-01-01T00:00:00.000Z',
    },
    {
      id: 'old', smartleadInboxId: 'old', smartleadClientId: 'client-1',
      email: 'old@older.com', deliverabilityScore: 99, campaignIds: [],
      numberOfCampaignAssociated: 0, createdAt: '2017-01-01T00:00:00.000Z',
    },
    {
      id: 'shared-2', smartleadInboxId: 'shared-2', smartleadClientId: 'client-1',
      email: 'second@shared.com', deliverabilityScore: 98, campaignIds: [],
      numberOfCampaignAssociated: 0, createdAt: '2016-01-01T00:00:00.000Z',
    },
  ];

  it('requests the documented multi-factor ranking and page limit', async () => {
    const db = memoryDatastore(rankingFixture());
    const { service } = subject(db);
    const returned = await service.getBestEmailAccountsForCampaign({
      smartleadClientId: 'client-1',
      campaignId: 'campaign-1',
      totalNumberOfEmailsToSend: 650,
      numberOfDaysInCampaign: 10,
      numberOfEmailPerDay: 20,
      numberOfEmailsPerInboxPerDay: 20,
    } as any);

    const applicationOrder = returned.map((account: any) => account.id);
    let aggregationIsCorrect = false;
    if (db.getManyAndAggregate.mock.calls.length) {
      const [filter, _context, pipeline, pagination] =
        db.getManyAndAggregate.mock.calls[0];
      const sort = pipeline.find((stage: any) => stage.$sort)?.$sort;
      aggregationIsCorrect =
        filter?.['data.smartleadClientId'] === 'client-1' &&
        sort?.['data.deliverabilityScore'] === -1 &&
        sort?.['data.numberOfCampaignAssociated'] === 1 &&
        sort?.otherEmailsUnderSameDomainCount === 1 &&
        sort?.['data.createdAt'] === 1 &&
        pipeline.some((stage: any) => stage.$lookup || stage.$group) &&
        pagination?.pageSize === 3;
    }
    expect(
      aggregationIsCorrect ||
        JSON.stringify(applicationOrder) === JSON.stringify(['old', 'new', 'shared']),
    ).toBe(true);
  });

  it('sizes a campaign pool from volume, duration, and daily capacity', async () => {
    const db = memoryDatastore(ranked(rankingFixture()));
    const { service } = subject(db);
    const result = await service.getBestEmailAccountsForCampaign({
      smartleadClientId: 'client-1',
      campaignId: 'campaign-1',
      totalNumberOfEmailsToSend: 650,
      numberOfDaysInCampaign: 10,
      numberOfEmailPerDay: 20,
      numberOfEmailsPerInboxPerDay: 20,
    } as any);
    expect(result).toHaveLength(3);
  });

  it('hydrates Smartlead reputation and creation time before saving', async () => {
    const db = memoryDatastore();
    const { service } = subject(db);
    jest.spyOn(global, 'fetch').mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({
        id: 'inbox-1',
        client_id: 'client-1',
        from_email: 'owner@example.com',
        createdAt: '2025-04-21T04:51:14.026Z',
        created_at: '2025-04-21T04:51:14.026Z',
        warmup_details: { warmup_reputation: 99 },
      }),
    } as any);

    await service.saveEmailAccount({
      email: 'owner@example.com',
      smartleadClientId: 'client-1',
      smartleadInboxId: 'inbox-1',
    });
    const stored = db.records.get('inbox-1');
    expect(stored).toEqual(
      expect.objectContaining({
        deliverabilityScore: 99,
        createdAt: '2025-04-21T04:51:14.026Z',
      }),
    );
  });

  it('surfaces a missing Smartlead inbox and delegates deletion safely', async () => {
    const db = memoryDatastore();
    const { service } = subject(db);
    jest.spyOn(global, 'fetch').mockResolvedValue({
      status: 404,
      ok: false,
      json: async () => ({}),
    } as any);
    await expect(
      service.saveEmailAccount({
        email: 'owner@example.com',
        smartleadClientId: 'client-1',
        smartleadInboxId: 'missing',
      }),
    ).rejects.toBeInstanceOf(NotFoundException);

    const deletionDb = memoryDatastore([
      {
        id: 'inbox-1', smartleadInboxId: 'inbox-1',
        email: 'owner@example.com', campaignIds: [],
      },
    ]);
    const deletionService = subject(deletionDb).service;
    await deletionService.deleteEmailAccount('inbox-1');
    expect(deletionDb.remove).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'inbox-1' }),
    );
    expect(deletionDb.records.has('inbox-1')).toBe(false);
  });
});
