from django.db import models
from datetime import date


class Stock(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)

    def price(self, at_date):
        """
        Retrieve the stock price on a specific date.
        If no price is available on that date, retrieve the latest price before that date.
        """
        try:
            # Attempt to get the exact price for the date
            stock_price = self.stockprice_set.get(date=at_date)
            return stock_price.price
        except StockPrice.DoesNotExist:
            # Fallback to the latest price before the given date
            stock_price = (
                self.stockprice_set.filter(date__lt=at_date).order_by("-date").first()
            )
            if stock_price:
                return stock_price.price
            else:
                return None  # No price available

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class StockPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateField()
    price = models.FloatField()

    class Meta:
        unique_together = ("stock", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.stock.symbol} on {self.date}: ${self.price:.2f}"


class Portfolio(models.Model):
    name = models.CharField(max_length=100)
    stocks = models.ManyToManyField(Stock, through="PortfolioStock")

    def total_value(self, at_date=None):
        """
        Calculate the total value of the portfolio at the current date or a specific date.
        If a stock's price is not available on the given date, it will be skipped.
        """
        if at_date is None:
            at_date = date.today()

        total = 0.0

        portfolio_stocks = self.portfoliostock_set.select_related("stock").all()
        for portfolio_stock in portfolio_stocks:
            stock_price = portfolio_stock.stock.price(at_date)
            if stock_price is not None:
                total += portfolio_stock.quantity * stock_price
            else:
                pass

        return total

    def profit(self, start_date, end_date):
        """
        Calculate the profit between two dates.
        Profit = Total value at end_date - Total value at start_date
        """
        if end_date < start_date:
            raise ValueError("end_date must be after start_date")

        start_value = self.total_value(at_date=start_date)
        end_value = self.total_value(at_date=end_date)
        return end_value - start_value

    def annualized_return(self, start_date, end_date):
        """
        Calculate the annualized return of the portfolio between two dates.
        Formula: ((End Value / Start Value) ** (1 / Years)) - 1
        where Years = Number of days between dates / 365.25
        """
        if end_date <= start_date:
            raise ValueError("end_date must be after start_date")

        start_value = self.total_value(at_date=start_date)
        end_value = self.total_value(at_date=end_date)

        if start_value == 0:
            return 0  # Avoid division by zero or undefined return

        days_between = (end_date - start_date).days
        years_between = days_between / 365.25  # Average accounting for leap years

        if years_between <= 0:
            return 0  # Handle very short durations

        annualized_return = (end_value / start_value) ** (1 / years_between) - 1
        return annualized_return

    def __str__(self):
        return self.name


class PortfolioStock(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    purchase_price = models.FloatField()
    date_purchased = models.DateField()

    def current_value(self):
        # Calculate current value of this stock in the portfolio
        return self.quantity * self.stock.price(date.today())

    def value_at(self, at_date):
        # Calculate value of this stock in the portfolio at a specific date
        return self.quantity * self.stock.price(at_date)

    def __str__(self):
        return f"{self.quantity} shares of {self.stock} purchased at ${self.purchase_price:.2f}"
